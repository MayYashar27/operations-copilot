"""Guards that make every Phase 0 run provably offline.

Phase 0 must never reach the Anthropic API (or any other host). Instead of
trusting that no code path calls the model, we make outbound connections
impossible for the whole process: any attempt raises NetworkBlocked.
"""

import os
import socket


class NetworkBlocked(RuntimeError):
    """Raised when evaluation code tries to open a network connection."""


_original_connect = socket.socket.connect
_original_connect_ex = socket.socket.connect_ex
_original_create_connection = socket.create_connection


LOOPBACK = {"127.0.0.1", "::1", "localhost"}


def _is_loopback(address) -> bool:
    host = address[0] if isinstance(address, tuple) and address else address
    return isinstance(host, str) and host in LOOPBACK


def _refuse_message():
    return NetworkBlocked(
        "Network access is disabled during offline evaluation. "
        "No API calls are allowed."
    )


def _guarded_connect(self, address):
    if not _is_loopback(address):
        raise _refuse_message()
    return _original_connect(self, address)


def _guarded_connect_ex(self, address):
    if not _is_loopback(address):
        raise _refuse_message()
    return _original_connect_ex(self, address)


def _guarded_create_connection(address, *args, **kwargs):
    if not _is_loopback(address):
        raise _refuse_message()
    return _original_create_connection(address, *args, **kwargs)


def block_network() -> None:
    """Make every outbound connection fail, except loopback.

    Loopback stays open because asyncio (used by FastAPI's test client) talks
    to itself over a local socket pair on Windows. Nothing on loopback can
    reach the Anthropic API.
    """
    socket.socket.connect = _guarded_connect
    socket.socket.connect_ex = _guarded_connect_ex
    socket.create_connection = _guarded_create_connection


def unblock_network() -> None:
    socket.socket.connect = _original_connect
    socket.socket.connect_ex = _original_connect_ex
    socket.create_connection = _original_create_connection


def offline_environment() -> None:
    """Block the network and make sure no real key is visible to the process.

    langgraph_agent builds a ChatAnthropic client at import time; that needs a
    key-shaped value but never sends a request unless invoked. A placeholder
    replaces any real key, so even an accidental call could not authenticate.
    """
    os.environ["ANTHROPIC_API_KEY"] = "phase0-offline-placeholder"
    block_network()
