import pytest

from quintain import utility


class TestTimeSeries:
    def test_get(self):
        ts = utility.TimeSeries(
            time=[0, 1, 3],
            values=[5, 4, 2],
        )
        assert ts.get(-1) == 5
        assert ts.get(0) == 5
        assert ts.get(1) == 4
        assert ts.get(2) == 4
        assert ts.get(3) == 2
        assert ts.get(4) == 2
