import asyncio
import sys

import pytest

from quintain.quintain import Connection, Port, Server, RealTimeServer
from quintain.controllers import Controller, Recorder, LookupTable
from quintain.services import CaptureAll, ModifyPorts
from quintain.utility import TimeSeries


@pytest.fixture(scope="module")
def timer_precision():
    """Set the precision of ``time.sleep`` under Windows."""
    if not sys.platform.startswith("win32"):
        yield
    else:
        # See https://docs.microsoft.com/en-us/windows/win32/api/timeapi/nf-timeapi-timebeginperiod
        import ctypes

        winmm = ctypes.WinDLL("winmm")
        winmm.timeBeginPeriod(1)
        yield
        winmm.timeEndPeriod(1)


class TestConnection:
    def test_transfer(self):
        sender = Port("sender", "foo")
        receiver = Port("receiver")
        Connection(sender, receiver).transfer()
        assert receiver.value == "foo"


class TestServer:
    def test_function(self):
        server = Server()
        server.add_device(
            "add_two", [Port("number", 0), Port("result", 0)], Controller(add_two)
        )
        server.add_device(
            "generator",
            [Port("number", 0)],
            LookupTable({"number": ([0, 1, 2], [3, 4, 5])}),
        )
        logger = Recorder()
        server.add_device("logger", [Port("result", None)], logger)
        server.add_connection("generator", "number", "add_two", "number")
        server.add_connection("add_two", "result", "logger", "result")

        for _ in range(5):
            server.next_cycle()
        assert logger.data == {"result": [None, 2, 5, 6, 7]}

    def test_with_services(self):
        server = Server()
        server.add_device(
            "add_two", [Port("number", 0), Port("result", 0)], Controller(add_two)
        )
        server.add_service(
            ModifyPorts(
                {"add_two": {"number": TimeSeries(time=[0, 1, 2], values=[3, 4, 5])}}
            ),
            priority=1,
        )
        capture_all = CaptureAll()
        server.add_service(capture_all)

        for _ in range(5):
            server.next_cycle()
        assert capture_all.data == {
            "add_two": {"number": [3, 4, 5, 5, 5], "result": [0, 5, 6, 7, 7]}
        }


class TestRealTimeServer:
    async def test_with_mock(self, mocker):
        duration = 0.1
        mock = mocker.Mock(next_cycle=mocker.Mock())
        server = RealTimeServer(mock, duration)

        server.start()
        await asyncio.sleep(0.5 * duration)
        assert mock.next_cycle.call_count == 1
        await asyncio.sleep(duration)
        assert mock.next_cycle.call_count == 2
        server.stop()
        await server.join()
        await asyncio.sleep(duration)
        assert mock.next_cycle.call_count == 2

    async def test_function(self):
        duration = 0.1
        server = RealTimeServer(duration=duration)
        server.add_device(
            "add_two", [Port("number", 0), Port("result", 0)], Controller(add_two)
        )
        server.add_device(
            "generator",
            [Port("number", 0)],
            LookupTable({"number": ([0, 1, 2], [3, 4, 5])}),
        )
        logger = Recorder()
        server.add_device("logger", [Port("result", None)], logger)
        server.add_connection("generator", "number", "add_two", "number")
        server.add_connection("add_two", "result", "logger", "result")

        server.start()
        await asyncio.sleep(4.5 * duration)
        server.stop()
        await server.join()
        assert logger.data == {"result": [None, 2, 5, 6, 7]}

    async def test_with_services(self):
        duration = 0.1
        server = RealTimeServer(duration=duration)
        server.add_device(
            "add_two", [Port("number", 0), Port("result", 0)], Controller(add_two)
        )
        server.add_service(
            ModifyPorts(
                {"add_two": {"number": TimeSeries(time=[0, 1, 2], values=[3, 4, 5])}}
            ),
            priority=1,
        )
        capture_all = CaptureAll()
        server.add_service(capture_all)

        server.start()
        await asyncio.sleep(4.5 * duration)
        server.stop()
        await server.join()
        assert capture_all.data == {
            "add_two": {"number": [3, 4, 5, 5, 5], "result": [0, 5, 6, 7, 7]}
        }


def add_two(ports, _):
    number = ports.get("number")
    result = ports.get("result")
    result.value = number.value + 2
