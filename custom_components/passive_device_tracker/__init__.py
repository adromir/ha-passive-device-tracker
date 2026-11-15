"""Passive Device Tracker integration."""

from __future__ import annotations

import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr

from .const import (
    DOMAIN,
    MANUFACTURER,
    DEFAULT_MODEL,
    CONF_LAN_MAC,
    CONF_WLAN_MAC,
    CONF_BT_MAC,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.DEVICE_TRACKER]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Passive Device Tracker from a config entry."""
    data = {**entry.data, **entry.options}

    # Register device in Home Assistant device registry with Omni Consumer Products
    dev_reg = dr.async_get(hass)
    connections: set[tuple[str, str]] = set()

    lan_mac = data.get(CONF_LAN_MAC)
    if lan_mac:
        connections.add((dr.CONNECTION_NETWORK_MAC, lan_mac))

    wlan_mac = data.get(CONF_WLAN_MAC)
    if wlan_mac:
        connections.add((dr.CONNECTION_NETWORK_MAC, wlan_mac))

    bt_mac = data.get(CONF_BT_MAC)
    if bt_mac:
        connections.add((dr.CONNECTION_BLUETOOTH, bt_mac))

    dev_reg.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, entry.entry_id)},
        connections=connections,
        name=entry.title,
        manufacturer=MANUFACTURER,
        model=DEFAULT_MODEL,
    )

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {}

    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await hass.config_entries.async_reload(entry.entry_id)
