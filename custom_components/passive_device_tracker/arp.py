"""ARP and neighbor table parsing utilities for passive_device_tracker."""

from __future__ import annotations

import asyncio
import logging
import os
import re
import sys

_LOGGER = logging.getLogger(__name__)

# Pattern for 6-octet hex MAC
_MAC_REGEX = re.compile(r"^([0-9a-fA-F]{2}[:-]){5}([0-9a-fA-F]{2})$")
_MAC_CLEAN = re.compile(r"[^0-9a-fA-F]")


def normalize_mac(mac: str | None) -> str | None:
    """Normalize MAC address to lowercase xx:xx:xx:xx:xx:xx format."""
    if not mac:
        return None
    mac = mac.strip()
    # Check if already colon or dash separated
    if _MAC_REGEX.match(mac):
        return mac.replace("-", ":").lower()

    # Check for Cisco-style xxxx.xxxx.xxxx or unseparated xxxxxxxxxxxx
    cleaned = _MAC_CLEAN.sub("", mac)
    if len(cleaned) == 12:
        return ":".join(cleaned[i : i + 2].lower() for i in range(0, 12, 2))

    return None


def parse_proc_net_arp(content: str) -> dict[str, str]:
    """Parse /proc/net/arp table content. Returns dict mapping MAC -> IP."""
    mac_to_ip: dict[str, str] = {}
    lines = content.splitlines()
    if not lines:
        return mac_to_ip

    for line in lines[1:]:  # skip header
        parts = line.split()
        if len(parts) >= 4:
            ip = parts[0]
            flags = parts[2]
            mac = parts[3]
            # Flag 0x2 indicates a complete ARP entry (0x0 is incomplete/stale)
            if flags == "0x2" and mac != "00:00:00:00:00:00":
                norm = normalize_mac(mac)
                if norm:
                    mac_to_ip[norm] = ip
    return mac_to_ip


def parse_ip_neigh(output: str) -> dict[str, str]:
    """Parse output of 'ip neigh' command. Returns dict mapping MAC -> IP."""
    mac_to_ip: dict[str, str] = {}
    for line in output.splitlines():
        parts = line.split()
        # Format: <ip> dev <dev> lladdr <mac> <STATE>
        if "lladdr" in parts:
            try:
                idx = parts.index("lladdr")
                if idx > 0 and idx + 1 < len(parts):
                    ip = parts[0]
                    mac = parts[idx + 1]
                    norm = normalize_mac(mac)
                    if norm:
                        mac_to_ip[norm] = ip
            except (ValueError, IndexError):
                continue
    return mac_to_ip


def parse_windows_arp(output: str) -> dict[str, str]:
    """Parse output of Windows 'arp -a' command. Returns dict mapping MAC -> IP."""
    mac_to_ip: dict[str, str] = {}
    for line in output.splitlines():
        parts = line.split()
        # Windows arp -a row: 192.168.2.1 aa-bb-cc-dd-ee-ff dynamic
        if len(parts) >= 2:
            ip = parts[0]
            mac = parts[1]
            norm = normalize_mac(mac)
            if norm and not norm.startswith("ff:ff:ff:ff:ff:ff"):
                mac_to_ip[norm] = ip
    return mac_to_ip


async def async_get_ip_for_mac(target_mac: str) -> str | None:
    """Resolve current IP address for a MAC address asynchronously."""
    norm_target = normalize_mac(target_mac)
    if not norm_target:
        return None

    # 1. Try reading /proc/net/arp (Fastest, native on Linux / Home Assistant OS)
    if os.path.exists("/proc/net/arp"):
        try:
            def _read_arp() -> str:
                with open("/proc/net/arp", "r", encoding="utf-8") as f:
                    return f.read()

            content = await asyncio.to_thread(_read_arp)
            mac_map = parse_proc_net_arp(content)
            if norm_target in mac_map:
                return mac_map[norm_target]
        except Exception as err:
            _LOGGER.debug("Failed to read /proc/net/arp: %s", err)

    # 2. Try 'ip neigh' on Linux
    if sys.platform != "win32":
        try:
            proc = await asyncio.create_subprocess_exec(
                "ip", "neigh",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=2.0)
            if proc.returncode == 0:
                mac_map = parse_ip_neigh(stdout.decode("utf-8", errors="ignore"))
                if norm_target in mac_map:
                    return mac_map[norm_target]
        except Exception as err:
            _LOGGER.debug("Failed to run 'ip neigh': %s", err)

    # 3. Try 'arp -a' fallback (Windows or Linux without /proc/net/arp)
    try:
        proc = await asyncio.create_subprocess_exec(
            "arp", "-a",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=2.0)
        if proc.returncode == 0:
            text = stdout.decode("utf-8", errors="ignore")
            mac_map = parse_windows_arp(text) if sys.platform == "win32" else parse_ip_neigh(text)
            if norm_target in mac_map:
                return mac_map[norm_target]
    except Exception as err:
        _LOGGER.debug("Failed to run 'arp -a': %s", err)

    return None
