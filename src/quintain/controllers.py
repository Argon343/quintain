from __future__ import annotations

from quintain.utility import TimeSeries


class Controller:
    def __init__(self, fn: Optional = None) -> None:
        """Simple controller which executes ``fn`` every cycle.

        Args:
            fn:
                A callable that takes a ``dict[str, Port]`` (noop by
                default)
        """
        self._fn = fn or (lambda ports, state: None)

    def execute(self, ports: dict[str, Port], state: State):
        self._fn(ports, state)


class Recorder:
    def __init__(self):
        """Captures the values of the controlled ports."""
        self._data = {}

    def execute(self, ports: dict[str, Port], _: State) -> None:
        for _, p in ports.items():
            values = self._data.get(p.name)
            if values is None:
                values = []
                self._data[p.name] = values
            values.append(p.value)

    @property
    def data(self):
        """The captured data.

        Maps port names to a list of values, which, at index ``i``,
        holds the value of the port at cycle ``i``.
        """
        return self._data


class LookupTable:
    def __init__(self, values: dict[str, tuple[list[float], list[_ValueType]]]) -> None:
        """Sets the values of all ports according to a provided lookup
        table.

        Args:
            values:
                Maps the name of the controlled ports to a pair of
                time and data values

        Raises:
            AssertionError: If for any pair the time and value lists
            don't have the same length
        """
        self._values = {
            k: TimeSeries(time, values) for k, (time, values) in values.items()
        }

    def execute(self, ports: dict[str, Port], state: State) -> None:
        for _, p in ports.items():
            p.value = self._values[p.name].get(state.cycles)
