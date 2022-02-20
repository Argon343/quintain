from __future__ import annotations

import bisect


class TimeSeries:
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
        # Find the right-most value less than ``t``.
        index = max(0, bisect.bisect_right(self._time, t) - 1)
        if index == len(self._time):
            index = -1
        return self._values[index]
