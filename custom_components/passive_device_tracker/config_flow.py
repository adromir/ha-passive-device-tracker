"""Config Flow and Options Flow for passive_device_tracker."""

from __future__ import annotations

import logging
from typing import Any
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
import homeassistant.helpers.config_validation as cv

from .arp import normalize_mac
from .const import (
    DOMAIN,
    CONF_NAME,
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
)

_LOGGER = logging.getLogger(__name__)


def is_bluetooth_available(hass) -> bool:
    """Check if Home Assistant has registered Bluetooth scanners."""
    try:
        from homeassistant.components import bluetooth
        return bool(bluetooth.async_scanner_count(hass) > 0)
    except Exception:
        return False


class PassiveDeviceTrackerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Passive Device Tracker."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize flow state."""
        self._device_name: str = ""
        self._selected_interfaces: list[str] = []

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step where user selects device name and interfaces."""
        errors: dict[str, str] = {}

        # Determine available interface options based on system capabilities
        has_bt = is_bluetooth_available(self.hass)
        available_interfaces = {
            INTERFACE_LAN: "LAN (Ethernet)",
            INTERFACE_WLAN: "WLAN (Wi-Fi)",
        }
        if has_bt:
            available_interfaces[INTERFACE_BLUETOOTH] = "Bluetooth (BLE)"

        if user_input is not None:
            name = user_input.get(CONF_NAME, "").strip()
            interfaces = user_input.get(CONF_INTERFACES, [])

            if not interfaces:
                errors["base"] = "no_interfaces_selected"
            else:
                self._device_name = name
                self._selected_interfaces = interfaces
                return await self.async_step_configure()

        schema = vol.Schema(
            {
                vol.Required(CONF_NAME): str,
                vol.Required(
                    CONF_INTERFACES,
                    default=[INTERFACE_LAN] if not has_bt else [INTERFACE_LAN, INTERFACE_BLUETOOTH],
                ): cv.multi_select(available_interfaces),
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
        )

    async def async_step_configure(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle configuring parameters for the chosen interfaces."""
        errors: dict[str, str] = {}

        if user_input is not None:
            clean_data: dict[str, Any] = {
                CONF_NAME: self._device_name,
                CONF_INTERFACES: self._selected_interfaces,
                CONF_CONSIDER_HOME: user_input.get(CONF_CONSIDER_HOME, DEFAULT_CONSIDER_HOME),
                CONF_PING_INTERVAL: user_input.get(CONF_PING_INTERVAL, DEFAULT_PING_INTERVAL),
            }

            # Validate LAN
            if INTERFACE_LAN in self._selected_interfaces:
                lan_ip = (user_input.get(CONF_LAN_IP) or "").strip()
                lan_mac = user_input.get(CONF_LAN_MAC)
                norm_lan_mac = normalize_mac(lan_mac) if lan_mac else None

                if lan_mac and not norm_lan_mac:
                    errors[CONF_LAN_MAC] = "invalid_mac"
                elif not lan_ip and not norm_lan_mac:
                    errors["base"] = "missing_lan_credentials"
                else:
                    if lan_ip:
                        clean_data[CONF_LAN_IP] = lan_ip
                    if norm_lan_mac:
                        clean_data[CONF_LAN_MAC] = norm_lan_mac

            # Validate WLAN
            if INTERFACE_WLAN in self._selected_interfaces:
                wlan_ip = (user_input.get(CONF_WLAN_IP) or "").strip()
                wlan_mac = user_input.get(CONF_WLAN_MAC)
                norm_wlan_mac = normalize_mac(wlan_mac) if wlan_mac else None

                if wlan_mac and not norm_wlan_mac:
                    errors[CONF_WLAN_MAC] = "invalid_mac"
                elif not wlan_ip and not norm_wlan_mac:
                    errors["base"] = "missing_wlan_credentials"
                else:
                    if wlan_ip:
                        clean_data[CONF_WLAN_IP] = wlan_ip
                    if norm_wlan_mac:
                        clean_data[CONF_WLAN_MAC] = norm_wlan_mac

            # Validate Bluetooth
            if INTERFACE_BLUETOOTH in self._selected_interfaces:
                bt_mac = user_input.get(CONF_BT_MAC)
                norm_bt_mac = normalize_mac(bt_mac) if bt_mac else None
                if not norm_bt_mac:
                    errors[CONF_BT_MAC] = "invalid_mac"
                else:
                    clean_data[CONF_BT_MAC] = norm_bt_mac

            if not errors:
                # Determine unique ID from primary MAC or device name
                primary_mac = (
                    clean_data.get(CONF_LAN_MAC)
                    or clean_data.get(CONF_WLAN_MAC)
                    or clean_data.get(CONF_BT_MAC)
                )
                unique_id = primary_mac or clean_data.get(CONF_LAN_IP) or clean_data.get(CONF_WLAN_IP) or self._device_name.lower().replace(" ", "_")
                
                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=self._device_name,
                    data=clean_data,
                )

        # Build dynamic fields based on selected interfaces
        fields: dict[Any, Any] = {}

        if INTERFACE_LAN in self._selected_interfaces:
            fields[vol.Optional(CONF_LAN_IP, default="")] = str
            fields[vol.Optional(CONF_LAN_MAC, default="")] = str

        if INTERFACE_WLAN in self._selected_interfaces:
            fields[vol.Optional(CONF_WLAN_IP, default="")] = str
            fields[vol.Optional(CONF_WLAN_MAC, default="")] = str

        if INTERFACE_BLUETOOTH in self._selected_interfaces:
            fields[vol.Required(CONF_BT_MAC)] = str

        fields[vol.Optional(CONF_CONSIDER_HOME, default=DEFAULT_CONSIDER_HOME)] = vol.All(
            vol.Coerce(int), vol.Range(min=10, max=3600)
        )
        fields[vol.Optional(CONF_PING_INTERVAL, default=DEFAULT_PING_INTERVAL)] = vol.All(
            vol.Coerce(int), vol.Range(min=5, max=300)
        )

        return self.async_show_form(
            step_id="configure",
            data_schema=vol.Schema(fields),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> PassiveDeviceTrackerOptionsFlowHandler:
        """Get the options flow for this handler."""
        return PassiveDeviceTrackerOptionsFlowHandler(config_entry)


class PassiveDeviceTrackerOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for Passive Device Tracker."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        errors: dict[str, str] = {}
        entry_data = {**self.config_entry.data, **self.config_entry.options}
        interfaces = entry_data.get(CONF_INTERFACES, [])

        if user_input is not None:
            updated_data = {**entry_data, **user_input}

            # Normalization & Validation
            if INTERFACE_LAN in interfaces:
                lan_ip = (user_input.get(CONF_LAN_IP) or "").strip()
                lan_mac = user_input.get(CONF_LAN_MAC)
                norm_lan_mac = normalize_mac(lan_mac) if lan_mac else None

                if lan_mac and not norm_lan_mac:
                    errors[CONF_LAN_MAC] = "invalid_mac"
                elif not lan_ip and not norm_lan_mac:
                    errors["base"] = "missing_lan_credentials"
                else:
                    updated_data[CONF_LAN_IP] = lan_ip
                    updated_data[CONF_LAN_MAC] = norm_lan_mac

            if INTERFACE_WLAN in interfaces:
                wlan_ip = (user_input.get(CONF_WLAN_IP) or "").strip()
                wlan_mac = user_input.get(CONF_WLAN_MAC)
                norm_wlan_mac = normalize_mac(wlan_mac) if wlan_mac else None

                if wlan_mac and not norm_wlan_mac:
                    errors[CONF_WLAN_MAC] = "invalid_mac"
                elif not wlan_ip and not norm_wlan_mac:
                    errors["base"] = "missing_wlan_credentials"
                else:
                    updated_data[CONF_WLAN_IP] = wlan_ip
                    updated_data[CONF_WLAN_MAC] = norm_wlan_mac

            if INTERFACE_BLUETOOTH in interfaces:
                bt_mac = user_input.get(CONF_BT_MAC)
                norm_bt_mac = normalize_mac(bt_mac) if bt_mac else None
                if not norm_bt_mac:
                    errors[CONF_BT_MAC] = "invalid_mac"
                else:
                    updated_data[CONF_BT_MAC] = norm_bt_mac

            if not errors:
                self.hass.config_entries.async_update_entry(
                    self.config_entry,
                    data=updated_data,
                )
                return self.async_create_entry(title="", data={})

        fields: dict[Any, Any] = {}

        if INTERFACE_LAN in interfaces:
            fields[vol.Optional(CONF_LAN_IP, default=entry_data.get(CONF_LAN_IP, ""))] = str
            fields[vol.Optional(CONF_LAN_MAC, default=entry_data.get(CONF_LAN_MAC, ""))] = str

        if INTERFACE_WLAN in interfaces:
            fields[vol.Optional(CONF_WLAN_IP, default=entry_data.get(CONF_WLAN_IP, ""))] = str
            fields[vol.Optional(CONF_WLAN_MAC, default=entry_data.get(CONF_WLAN_MAC, ""))] = str

        if INTERFACE_BLUETOOTH in interfaces:
            fields[vol.Required(CONF_BT_MAC, default=entry_data.get(CONF_BT_MAC, ""))] = str

        fields[vol.Optional(
            CONF_CONSIDER_HOME,
            default=entry_data.get(CONF_CONSIDER_HOME, DEFAULT_CONSIDER_HOME),
        )] = vol.All(vol.Coerce(int), vol.Range(min=10, max=3600))

        fields[vol.Optional(
            CONF_PING_INTERVAL,
            default=entry_data.get(CONF_PING_INTERVAL, DEFAULT_PING_INTERVAL),
        )] = vol.All(vol.Coerce(int), vol.Range(min=5, max=300))

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(fields),
            errors=errors,
        )
