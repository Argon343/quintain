# quintain

**quintain** is a tool for simulating hardware interactions.

Every _client_ has _ports_, which hold a value and are connected to ports of the
same or other devices. Every _cycle_, the connections transfer data from sender
to receiver, and each devices' _controller_ changes state and/or modifies the
value of the device's ports.

The cycles are either advanced manually by calling `next_cycle`, or by using a
real-time server, which periodically advances the cycle by running a task on an
`asyncio` event loop.

## Usage

### Getting Started

Start by creating a server:

```python
from quintain.quintain import Port, Server
from quintain.controller import Controller, LookupTable, Recorder

server = Server()
```

We add devices to the server using `add_device`:

```python
def add_two(ports):
    number = ports.get("in")
    result = ports.get("out")
    result.value = number.value + 2

server.add_device(
    name="main",
    ports=[Port("in", 0), Port("out", 0)],
    controller=Controller(add_two),
)
```

This adds a device `"main"` to the server. The device has two ports, `"in"` and
`"out"`, each with default value zero. The controller calls the function
`add_two` on the ports of the device. In this case, it add `2` to the value of
`"in"` and writes it to `"out"`. Basically, the controller adds logic to
the otherwise dumb device.

We add two other devices to the setup, one for capturing the values of `"out"`,
and one for modifying the values of `"in"`:

```python
server.add_device(
    name="lookup",
    ports=[Port("values", 0)],
    controller=LookupTable({"values": ([0, 1, 2], [3, 4, 5])}),
)
recorder = Recorder()
server.add_device(
    name="recorder",
    ports=[Port("capture", None)],
    controller=recorder
)
```

The `LookupTable` controller takes a `dict` which maps port names to pairs. Each
pair describes a time series: The first component contains time points (each
time point describes a cycle at which the value of the time series changes), the
second component contains the values. On every cycle specified by the time
series, the controller changes the value of the respective port to the value
specified by the time series.

For example, the controller above sets th value of `"values"` to `3` on the
first cycle, to `4` on the second, to `5` on the third. The value remains set to
`5` for the rest of the simulation.

The `Recorder` records the values of its port. The values can be acquired by
using the `data` property.

Before running the simulation, we need to add connections between the devices:

```python
server.add_connection("lookup", "values", "main", "in")
server.add_connection("main", "out", "recorder", "capture")
```

For example, the first call connects port `"values"` of device `"lookup"` to
port `"in"` of `"main"`.

Now we can run the simulation by calling `next_cycle` to advance time by one time unit:

```python
for _ in range(5):
    server.next_cycle()
```

Let's check out the results of the simulation:

```python
assert recorder.data == {"capture": [None, 2, 5, 6, 7]}
```


### Real-Time Server

The `RealTimeServer` class of **quintain** implements virtually the same interface as
`Server`, but is able to operate asynchronously using `asyncio`:

```python
duration = 0.1
server = RealTimeServer(duration=duration)

def add_two(ports):
    number = ports.get("in")
    result = ports.get("out")
    result.value = number.value + 2

server.add_device(
    name="main",
    ports=[Port("in", 0), Port("out", 0)],
    controller=Controller(add_two),
)
server.add_device(
    name="lookup",
    ports=[Port("values", 0)],
    controller=LookupTable({"values": ([0, 1, 2], [3, 4, 5])}),
)
recorder = Recorder()
server.add_device(
    name="recorder",
    ports=[Port("capture", None)],
    controller=recorder
)

server.add_connection("lookup", "values", "main", "in")
server.add_connection("main", "out", "recorder", "capture")

server.start()
await asyncio.sleep(4.5 * duration)  # Block while the server works
server.stop()
await server.join()  # Wait until the server is gracefully closed
assert recorder.data == {"capture": [None, 2, 5, 6, 7]}
```

The `duration: float` parameter determines the interval between two cycles in
seconds.


### Custom Controllers

**quintain** contains some examples of controllers in the
`quintain.controllers` module. You can create your own controllers by
implementing the following interface:

```python
class AbstractController:
    def execute(self, ports: dict[str, Port]):
        pass
```

Every cycle, `execute()` is called on the device's ports.
