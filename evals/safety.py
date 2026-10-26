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


def _refuse(*_args, **_kwargs):
    raise NetworkBlocked(
        "Network access is disabled during Phase 0 evaluation. "
        "No API calls are allowed."
    )


def block_network() -> None:
    """Make every outbound socket connection fail for this process."""
    socket.socket.connect = _refuse
    socket.socket.connect_ex = _refuse
    socket.create_connection = _refuse


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
