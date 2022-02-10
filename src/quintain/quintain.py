from __future__ import annotations

import asyncio
import bisect
from collections import OrderedDict
import dataclasses
import time

from quintain.exceptions import (
    NoSuchPort,
    NoSuchDevice,
    InvalidDuration,
    DuplicateDeviceError,
)


@dataclasses.dataclass
class Port:
    name: str
    value: Optional = None


@dataclasses.dataclass
class Connection:
    sender: Port
    receiver: Port

    def transfer(self) -> None:
        """Transfer data from sender to receiver."""
        self.receiver.value = self.sender.value


class State:
    def __init__(self):
        """A class for storing global state."""
        self._cycles = 0
        self._user = {}  # Stores server-specific data

    @property
    def cycles(self) -> int:
        return self._cycles

    @property
    def user(self) -> dict:
        return self._user


class AbstractController:
    def execute(self, ports: dict[str, Port], state: State) -> None:
        pass


class AbstractService:
    def execute(
        self, clients: dict[str, Client], connections: list[Connection], state: State
    ) -> None:
        pass


class Client:
    def __init__(
        self,
        name: str,
        ports: list[Port],
        controller: Optional[AbstractController] = None,
    ) -> None:
        """Client/device class.

        Args:
            name: The name of the client
            ports: The ports of the device
            controller: The internal logic of the device
        """
        self._name = name
        self._ports = {p.name: p for p in ports}
        self._controller = controller

    @property
    def name(self) -> str:
        return self._name

    @property
    def ports(self) -> dict[str, Port]:
        return self._ports

    def fn(self, state: State) -> None:
        """Execute the device's internal logic."""
        if self._controller is None:
            return
        self._controller.execute(self._ports, state)


class Server:
    def __init__(self, state: Optional[State] = None) -> None:
        self._services: list[tuple[int, Service]] = []
        self._clients: dict[str, Client] = {}
        self._connections: list[Connection] = []
        self._state = state or State()

    def next_cycle(self) -> None:
        """Advance to the next cycle.

        This function executes all controllers present on the server and
        then transfers data through the connections.
        """
        for _, s in reversed(self._services):
            s.execute(self._clients, self._connections, self._state)
        for _, c in self._clients.items():
            c.fn(self._state)
        for c in self._connections:
            c.transfer()
        self._state._cycles += 1  # _cycles is considered public in this module

    def add_device(
        self,
        name: str,
        ports: list[Port],
        controller: Optional[AbstractController] = None,
    ) -> None:
        """Add a device with controller to the server.

        Args:
            name: The name of the new device
            ports: The ports of the new device
            controller: The controller of the new device

        Raises:
            DuplicateDeviceError:
                If there already exists a device with the same name on
                the server
        """
        if name in self._clients:
            raise DuplicateDeviceError(f"Device with name '{name}' already exists")
        client = Client(name, ports, controller)
        self._clients[name] = client

    def add_connection(
        self,
        sender_device: str,
        sender_port: str,
        receiver_device: str,
        receiver_port: str,
    ) -> None:
        """Connect two ports on the server.

        Args:
            sender_device: The name of the device from which to send
            sender_port: The name of the port from which to send
            receiver_device: The name of the device on which to receive
            receiver_port: The name of the port on which to receive

        Raises:
            NoSuchDevice:
                If ``sender_device`` or ``receiver_device`` doesn't
                exist
            NoSuchPort:
                If ``sender_port`` is not found in ``sender_device`` or
                ``receiver_port`` is not found in ``receiver_device``
        """
        sender = self._get_port(sender_device, sender_port)
        receiver = self._get_port(receiver_device, receiver_port)
        # TODO Check for dimension, type, direction mismatches and
        # multiple inputs (an output can connect to multiple inputs, but
        # each input can have at most one output)!
        self._connections.append(Connection(sender, receiver))

    def add_service(self, service: AbstractService, priority: int = 0) -> None:
        """Add a service to the server.

        Args:
            service: The service to add
            priority: The priority of the service

        Services with higher priority are executed before those with lower priority.
        """
        # Note that tuples are by default ordered by their first,
        # element, then the second one, etc.
        bisect.insort(self._services, (priority, service))

    def _get_port(self, device: str, port: str) -> Port:
        """Get a port by name.

        Args:
            device: Name of the device that the port belong to
            port: Name of the port

        Raises:
            NoSuchDevice: If ``device`` doesn't exist
            NoSuchPort: If ``port`` is not found in ``device``
        """
        d = self._clients.get(device)
        if d is None:
            raise NoSuchDevice(device)
        p = d.ports.get(port)
        if p is None:
            raise NoSuchPort(port)
        return p


class RealTimeServer:
    def __init__(
        self, server: Optional[Server] = None, duration: float = 0.0, timer=None
    ) -> None:
        """Real-time server for rogue.

        Args:
            duration:
                The frame duration, i.e. interval between ``next_cycle``
                calls (in seconds)
            timer:
                A callable which returns the current time (default is
                ``time.perf_counter``)

        Raises:
            InvalidDuration: If ``duration`` is negative

        Asynchronously calls ``self.next_cycle()`` repeatedly using
        ``asyncio``. Each frame is ``duration`` seconds long.
        """
        if duration < 0:
            raise InvalidDuration("duration must be non-negative")
        self._duration = duration
        self._grain = duration / 1000.0
        # `self._precision` is picked so that measurements are taken too
        # early about 50% of the time.
        self._precision = self._grain / 2
        self._start_time = None

        self._server = server or Server()
        self._task = None
        self._event = asyncio.Event()
        self._timer = timer or time.perf_counter

    def start(self, name: Optional[str] = None) -> None:
        """Start the server.

        Note that this requires a running ``asyncio`` event loop in the
        background.
        """
        name = name or "quintain"
        self._start_time = self._timer()
        self._task = asyncio.create_task(self.serve(), name=name)

    def stop(self) -> None:
        """Stop the daemon job."""
        self._event.set()

    async def join(self) -> None:
        """Wait until done."""
        await self._task

    async def serve(self) -> None:
        """Loop that repeatedly calls ``next_cycle`` of the wrapped
        server.

        Most likely you should not use this directly, and instead use
        ``start()`` to run the server.
        """
        cycles = 0
        start_time = self._timer()
        while not self._event.is_set():
            current = self._timer()
            next_ = start_time + cycles * self._duration
            if current > next_ - self._precision:
                cycles += 1
                self._server.next_cycle()
            await asyncio.sleep(self._grain)

    def add_connection(
        self,
        sender_device: str,
        sender_port: str,
        receiver_device: str,
        receiver_port: str,
    ) -> None:
        """Connect two ports on the server.

        Args:
            sender_device: The name of the device from which to send
            sender_port: The name of the port from which to send
            receiver_device: The name of the device on which to receive
            receiver_port: The name of the port on which to receive

        Raises:
            NoSuchDevice:
                If ``sender_device`` or ``receiver_device`` doesn't
                exist
            NoSuchPort:
                If ``sender_port`` is not found in ``sender_device`` or
                ``receiver_port`` is not found in ``receiver_device``
        """
        self._server.add_connection(
            sender_device, sender_port, receiver_device, receiver_port
        )

    def add_device(
        self,
        name: str,
        ports: list[Port],
        controller: Optional[AbstractController] = None,
    ) -> None:
        """Add a device with controller to the server.

        Args:
            name: The name of the new device
            ports: The ports of the new device
            controller: The controller of the new device

        Raises:
            DuplicateDeviceError:
                If there already exists a device with the same name on
                the server
        """
        self._server.add_device(name, ports, controller)
