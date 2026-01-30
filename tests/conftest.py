import pytest


def pytest_runtest_setup(item):
    # global skip for hardware-dependent tests marked by filename
    hardware_files = {
        "test_connection.py",
        "test_connection_class.py",
        "test_connection_class_simulator.py",
    }
    if item.fspath.basename in hardware_files:
        pytest.skip("Wymaga fizycznego kontrolera LED/ESP.")
