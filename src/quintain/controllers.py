from __future__ import annotations

import bisect


class Controller:
    def __init__(self, fn) -> None:
        """Simple controller which executes ``fn`` every cycle.

        Args:
            fn: A callable that takes a ``dict[str, Port]``
        """
        self._fn = fn

    def execute(self, ports: dict[str, Port]):
        self._fn(ports)


class Recorder:
    def __init__(self):
        """Captures the values of the controlled ports."""
        self._data = {}
        self._cycles = 0

    def execute(self, ports: dict[str, Port]) -> None:
        for _, p in ports.items():
            values = self._data.get(p.name)
            if values is None:
                values = []
                self._data[p.name] = values
            values.append(p.value)
        self._cycles += 1

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
            k: _TimeSeries(time, values) for k, (time, values) in values.items()
        }
        self._cycles = 0

    def execute(self, ports: dict[str, Port]) -> None:
        for _, p in ports.items():
            p.value = self._values[p.name].get(self._cycles)
        self._cycles += 1


class _TimeSeries:
    def __init__(self, time: list[float], values: list[_ValueType]) -> None:
        """Time series object that interpolates data points.

        Args:
            time: The time points
            values: The data points

        Raises:
            AssertionError: If both lists don't have the same length
        """
        assert len(time) == len(values)
        self._time = time
        self._values = values

    def get(self, t):
        """Return the value of the timeseries at time ``t``.

        If ``t`` is not in ``self._time``, then the value is
        interpolated by using the value of the previous time point.
        """
        index = bisect.bisect_left(self._time, t)
        if index == len(self._time):
            index = -1
        return self._values[index]
