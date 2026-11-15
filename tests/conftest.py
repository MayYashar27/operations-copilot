"""The test suite must never reach a remote service, including the Anthropic API.

Outbound connections are refused for the whole session; loopback stays open
for FastAPI's test client. A test that accidentally calls the real model
fails immediately instead of sending a request.
"""

import socket

import pytest

_LOOPBACK = {"127.0.0.1", "::1", "localhost"}
_connect = socket.socket.connect
_create_connection = socket.create_connection


def _host(address):
    return address[0] if isinstance(address, tuple) and address else address


def _guarded_connect(self, address):
    if _host(address) not in _LOOPBACK:
        raise RuntimeError(f"Tests must not open network connections (attempted {_host(address)}).")
    return _connect(self, address)


def _guarded_create_connection(address, *args, **kwargs):
    if _host(address) not in _LOOPBACK:
        raise RuntimeError(f"Tests must not open network connections (attempted {_host(address)}).")
    return _create_connection(address, *args, **kwargs)


@pytest.fixture(autouse=True, scope="session")
def no_network():
    socket.socket.connect = _guarded_connect
    socket.create_connection = _guarded_create_connection
    yield
    socket.socket.connect = _connect
    socket.create_connection = _create_connection
