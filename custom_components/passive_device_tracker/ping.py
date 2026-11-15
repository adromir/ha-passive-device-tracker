"""Asynchronous ping implementation for passive_device_tracker."""

from __future__ import annotations

import asyncio
import logging
import re
import sys

_LOGGER = logging.getLogger(__name__)

# Matches "time=12.4 ms" or "time<1ms" or "Zeit=12ms" or "Zeit<1ms"
_LATENCY_REGEX = re.compile(r"(?:time|zeit)[=<]([0-9.]+)\s*ms", re.IGNORECASE)


async def async_ping(host: str, timeout: int = 2) -> tuple[bool, float | None]:
    """Ping a host asynchronously without blocking.

    Returns (is_reachable, latency_ms).
    """
    if not host or not host.strip():
        return False, None

    host = host.strip()

    if sys.platform == "win32":
        cmd = ["ping", "-n", "1", "-w", str(int(timeout * 1000)), host]
    else:
        # Linux / Home Assistant OS
        cmd = ["ping", "-c", "1", "-W", str(int(timeout)), host]

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=float(timeout + 2))
        if proc.returncode == 0:
            output = stdout.decode("utf-8", errors="ignore")
            latency = _parse_latency(output)
            return True, latency
        return False, None
    except asyncio.TimeoutError:
        _LOGGER.debug("Ping to %s timed out after %s seconds", host, timeout)
        return False, None
    except Exception as err:
        _LOGGER.debug("Error pinging %s: %s", host, err)
        return False, None


def _parse_latency(ping_output: str) -> float | None:
    """Extract latency in milliseconds from ping output."""
    match = _LATENCY_REGEX.search(ping_output)
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            pass
    return None
