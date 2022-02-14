from __future__ import annotations

from quintain.utility import TimeSeries


class CaptureAll:
    def __init__(self):
        """A service that captures the data of all ports on the server."""
        self._data = {}

    @property
    def data(self) -> dict[str, dict[str, _Value]]:
        """The captured data.

        Maps device names to a dictionary that maps ports names to the
        captured data.
        """
        return self._data

    def execute(self, clients, connections, state) -> None:
        del connections
        del state
        for _, client in clients.items():
            ports = self._data.get(client.name)
            if ports is None:
                ports = {}
                self._data[client.name] = ports
            for _, port in client.ports.items():
                values = ports.get(port.name)
                if values is None:
                    values = []
                    ports[port.name] = values
                values.append(port.value)


class ModifyPorts:
    def __init__(self, values: dict[str, dict[str, TimeSeries]]) -> None:
        self._values = values

    def execute(self, clients, connections, state) -> None:
        del connections
        for client_name, values in self._values.items():
            client = clients[client_name]
            for port, ts in values.items():
                client.ports.get(port).value = ts.get(state.cycles)
