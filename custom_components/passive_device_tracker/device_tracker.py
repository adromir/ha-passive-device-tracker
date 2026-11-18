"""Passive Device Tracker entity implementation."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import logging
from typing import Any, Callable

from homeassistant.components.device_tracker import ScannerEntity, SourceType
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
import homeassistant.util.dt as dt_util

from .arp import async_get_ip_for_mac
from .const import (
    DOMAIN,
    CONF_INTERFACES,
    INTERFACE_LAN,
    INTERFACE_WLAN,
    INTERFACE_BLUETOOTH,
    CONF_LAN_IP,
    CONF_LAN_MAC,
    CONF_WLAN_IP,
    CONF_WLAN_MAC,
    CONF_BT_MAC,
    CONF_CONSIDER_HOME,
    DEFAULT_CONSIDER_HOME,
    CONF_PING_INTERVAL,
    DEFAULT_PING_INTERVAL,
    CONF_PING_TIMEOUT,
    DEFAULT_PING_TIMEOUT,
    ATTR_LAST_SEEN_BY,
    ATTR_ACTIVE_INTERFACES,
    ATTR_LAN_STATUS,
    ATTR_WLAN_STATUS,
    ATTR_BT_STATUS,
    ATTR_LAN_IP,
    ATTR_WLAN_IP,
    ATTR_BT_RSSI,
    ATTR_CONSIDER_HOME,
)
from .ping import async_ping

_LOGGER = logging.getLogger(__name__)


def _utcnow() -> datetime:
    """Return current UTC datetime."""
    try:
        return dt_util.utcnow()
    except Exception:
        return datetime.now(timezone.utc)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up device tracker entity for this config entry."""
    entity = PassiveDeviceTrackerEntity(entry)
    async_add_entities([entity])


class PassiveDeviceTrackerEntity(ScannerEntity):
    """Passive device tracker entity supporting LAN, WLAN, and Bluetooth LE."""

    _attr_has_entity_name = True
    _attr_name = None
    _attr_icon = "mdi:devices"

    def __init__(self, entry: ConfigEntry) -> None:
        """Initialize the tracker entity."""
        self.entry = entry
        self._data = {**entry.data, **entry.options}
        self._attr_unique_id = f"{entry.entry_id}_tracker"

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
        )

        self._interfaces: list[str] = self._data.get(CONF_INTERFACES, [])
        self._lan_ip: str = self._data.get(CONF_LAN_IP, "")
        self._lan_mac: str | None = self._data.get(CONF_LAN_MAC)
        self._wlan_ip: str = self._data.get(CONF_WLAN_IP, "")
        self._wlan_mac: str | None = self._data.get(CONF_WLAN_MAC)
        self._bt_mac: str | None = self._data.get(CONF_BT_MAC)

        self._consider_home: int = self._data.get(CONF_CONSIDER_HOME, DEFAULT_CONSIDER_HOME)
        self._ping_interval: int = self._data.get(CONF_PING_INTERVAL, DEFAULT_PING_INTERVAL)
        self._ping_timeout: int = self._data.get(CONF_PING_TIMEOUT, DEFAULT_PING_TIMEOUT)

        self._last_seen: datetime | None = None
        self._last_seen_by: str | None = None
        self._lan_online: bool = False
        self._wlan_online: bool = False
        self._bt_online: bool = False

        self._lan_latency: float | None = None
        self._wlan_latency: float | None = None
        self._bt_rssi: int | None = None

        self._current_lan_ip: str = self._lan_ip
        self._current_wlan_ip: str = self._wlan_ip

        self._ping_task: asyncio.Task | None = None
        self._cancel_bt_callback: Callable | None = None

    @property
    def source_type(self) -> SourceType:
        """Return the source type of the device."""
        if self._last_seen_by == INTERFACE_BLUETOOTH:
            return SourceType.BLUETOOTH_LE
        return SourceType.ROUTER

    @property
    def is_connected(self) -> bool:
        """Return true if device was seen within consider_home seconds."""
        if self._last_seen is None:
            return False
        elapsed = (_utcnow() - self._last_seen).total_seconds()
        return elapsed < self._consider_home

    @property
    def ip_address(self) -> str | None:
        """Return the primary IP address of the device."""
        if self._last_seen_by == INTERFACE_WLAN and self._current_wlan_ip:
            return self._current_wlan_ip
        return self._current_lan_ip or self._current_wlan_ip or None

    @property
    def mac_address(self) -> str | None:
        """Return the primary MAC address of the device."""
        if self._last_seen_by == INTERFACE_WLAN and self._wlan_mac:
            return self._wlan_mac
        if self._last_seen_by == INTERFACE_BLUETOOTH and self._bt_mac:
            return self._bt_mac
        return self._lan_mac or self._wlan_mac or self._bt_mac or None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return device tracker attributes."""
        attrs: dict[str, Any] = {
            ATTR_ACTIVE_INTERFACES: self._interfaces,
            ATTR_LAST_SEEN_BY: self._last_seen_by,
            ATTR_CONSIDER_HOME: self._consider_home,
            "last_seen": self._last_seen.isoformat() if self._last_seen else None,
        }

        if INTERFACE_LAN in self._interfaces:
            attrs[ATTR_LAN_STATUS] = self._lan_online
            attrs[ATTR_LAN_IP] = self._current_lan_ip
            attrs["lan_mac"] = self._lan_mac
            attrs["lan_latency_ms"] = self._lan_latency

        if INTERFACE_WLAN in self._interfaces:
            attrs[ATTR_WLAN_STATUS] = self._wlan_online
            attrs[ATTR_WLAN_IP] = self._current_wlan_ip
            attrs["wlan_mac"] = self._wlan_mac
            attrs["wlan_latency_ms"] = self._wlan_latency

        if INTERFACE_BLUETOOTH in self._interfaces:
            attrs[ATTR_BT_STATUS] = self._bt_online
            attrs["bluetooth_mac"] = self._bt_mac
            attrs[ATTR_BT_RSSI] = self._bt_rssi

        return attrs

    def _update_seen(
        self,
        source: str,
        timestamp: datetime,
        latency: float | None = None,
        rssi: int | None = None,
    ) -> None:
        """Update last seen status for a source."""
        self._last_seen = timestamp
        self._last_seen_by = source

        if source == INTERFACE_LAN:
            self._lan_online = True
            self._lan_latency = latency
        elif source == INTERFACE_WLAN:
            self._wlan_online = True
            self._wlan_latency = latency
        elif source == INTERFACE_BLUETOOTH:
            self._bt_online = True
            self._bt_rssi = rssi

    async def async_added_to_hass(self) -> None:
        """Start tracking when entity is added to Home Assistant."""
        await super().async_added_to_hass()

        # Start periodic network ping task if LAN or WLAN is configured
        if INTERFACE_LAN in self._interfaces or INTERFACE_WLAN in self._interfaces:
            self._ping_task = asyncio.create_task(self._ping_loop())

        # Register passive Bluetooth callback if Bluetooth is configured
        if INTERFACE_BLUETOOTH in self._interfaces and self._bt_mac:
            self._setup_bluetooth_listener()

    async def async_will_remove_from_hass(self) -> None:
        """Clean up background tasks and callbacks."""
        if self._ping_task and not self._ping_task.done():
            self._ping_task.cancel()
            try:
                await self._ping_task
            except asyncio.CancelledError:
                pass

        if self._cancel_bt_callback:
            self._cancel_bt_callback()
            self._cancel_bt_callback = None

        await super().async_will_remove_from_hass()

    def _setup_bluetooth_listener(self) -> None:
        """Register passive Bluetooth callback with Home Assistant bluetooth component."""
        try:
            from homeassistant.components import bluetooth
            norm_mac = self._bt_mac.lower() if self._bt_mac else ""
            if hasattr(bluetooth, "async_register_callback"):
                self._cancel_bt_callback = bluetooth.async_register_callback(
                    self.hass,
                    self._handle_bluetooth_advertisement,
                    {"address": norm_mac},
                    bluetooth.BluetoothScanningMode.PASSIVE,
                )
        except Exception as err:
            _LOGGER.debug("Could not register passive Bluetooth callback: %s", err)

    @callback
    def _handle_bluetooth_advertisement(self, service_info: Any, change: Any = None) -> None:
        """Handle incoming passive Bluetooth advertisement."""
        rssi = getattr(service_info, "rssi", None)
        self._update_seen(INTERFACE_BLUETOOTH, _utcnow(), rssi=rssi)
        self.async_write_ha_state()

    async def _ping_loop(self) -> None:
        """Periodic background loop for pinging LAN and WLAN."""
        while True:
            try:
                tasks = []
                if INTERFACE_LAN in self._interfaces:
                    tasks.append(self._check_lan())
                if INTERFACE_WLAN in self._interfaces:
                    tasks.append(self._check_wlan())

                if tasks:
                    await asyncio.gather(*tasks, return_exceptions=True)

                self.async_write_ha_state()
            except asyncio.CancelledError:
                break
            except Exception as err:
                _LOGGER.debug("Error in ping loop for %s: %s", self.entity_id, err)

            try:
                await asyncio.sleep(self._ping_interval)
            except asyncio.CancelledError:
                break

    async def _check_lan(self) -> None:
        """Check LAN connection via unicast ping and dynamic ARP resolution."""
        ip_to_ping = self._current_lan_ip

        # If IP is missing or if ping previously failed, try resolving current IP via MAC
        if not ip_to_ping and self._lan_mac:
            resolved = await async_get_ip_for_mac(self._lan_mac)
            if resolved:
                self._current_lan_ip = resolved
                ip_to_ping = resolved

        if not ip_to_ping:
            self._lan_online = False
            return

        is_up, latency = await async_ping(ip_to_ping, timeout=self._ping_timeout)
        if is_up:
            self._update_seen(INTERFACE_LAN, _utcnow(), latency=latency)
        else:
            self._lan_online = False
            # If ping failed and we have a MAC, try re-resolving in case DHCP IP changed
            if self._lan_mac:
                new_ip = await async_get_ip_for_mac(self._lan_mac)
                if new_ip and new_ip != ip_to_ping:
                    self._current_lan_ip = new_ip
                    # Retry ping with newly discovered DHCP IP
                    retry_up, retry_latency = await async_ping(new_ip, timeout=self._ping_timeout)
                    if retry_up:
                        self._update_seen(INTERFACE_LAN, _utcnow(), latency=retry_latency)

    async def _check_wlan(self) -> None:
        """Check WLAN connection via unicast ping and dynamic ARP resolution."""
        ip_to_ping = self._current_wlan_ip

        if not ip_to_ping and self._wlan_mac:
            resolved = await async_get_ip_for_mac(self._wlan_mac)
            if resolved:
                self._current_wlan_ip = resolved
                ip_to_ping = resolved

        if not ip_to_ping:
            self._wlan_online = False
            return

        is_up, latency = await async_ping(ip_to_ping, timeout=self._ping_timeout)
        if is_up:
            self._update_seen(INTERFACE_WLAN, _utcnow(), latency=latency)
        else:
            self._wlan_online = False
            if self._wlan_mac:
                new_ip = await async_get_ip_for_mac(self._wlan_mac)
                if new_ip and new_ip != ip_to_ping:
                    self._current_wlan_ip = new_ip
                    retry_up, retry_latency = await async_ping(new_ip, timeout=self._ping_timeout)
                    if retry_up:
                        self._update_seen(INTERFACE_WLAN, _utcnow(), latency=retry_latency)
