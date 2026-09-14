"""Transport errors must never silently repeat a scan with different arguments."""
import pytest
from board.connection import Connection


def test_internal_type_error_does_not_repeat_scan() -> None:
    class Backend:
        calls = 0
        def scan_board(self, positions, **kwargs):
            self.calls += 1
            raise TypeError("malformed data")
    connection = Connection.__new__(Connection)
    connection._backend = Backend()
    with pytest.raises(TypeError, match="malformed data"):
        connection.scan_board([(1, 2)], timeout_s=3)
    assert connection._backend.calls == 1
