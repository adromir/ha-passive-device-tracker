"""Tests for config_flow."""

import unittest
from unittest.mock import AsyncMock, MagicMock, patch

import tests.ha_mock  # noqa: F401

from custom_components.passive_device_tracker.config_flow import (
    PassiveDeviceTrackerConfigFlow,
    is_bluetooth_available,
)
from custom_components.passive_device_tracker.const import (
    CONF_NAME,
    CONF_INTERFACES,
    INTERFACE_LAN,
    INTERFACE_WLAN,
    INTERFACE_BLUETOOTH,
    CONF_LAN_IP,
    CONF_LAN_MAC,
    CONF_BT_MAC,
    CONF_CONSIDER_HOME,
)


class TestConfigFlow(unittest.IsolatedAsyncioTestCase):
    """Test passive_device_tracker config flow."""

    async def test_bluetooth_capability_detection(self):
        """Test detection of Bluetooth capability."""
        mock_hass = MagicMock()
        import sys
        comp_mod = sys.modules.get("homeassistant.components")

        # Case 1: bluetooth component not loaded
        if hasattr(comp_mod, "bluetooth"):
            delattr(comp_mod, "bluetooth")
        with patch.dict("sys.modules", {"homeassistant.components.bluetooth": None}):
            self.assertFalse(is_bluetooth_available(mock_hass))

        # Case 2: bluetooth loaded with scanner_count = 0
        mock_bt = MagicMock()
        mock_bt.async_scanner_count.return_value = 0
        comp_mod.bluetooth = mock_bt
        with patch.dict("sys.modules", {"homeassistant.components.bluetooth": mock_bt}):
            self.assertFalse(is_bluetooth_available(mock_hass))

        # Case 3: bluetooth loaded with scanner_count > 0
        mock_bt.async_scanner_count.return_value = 1
        comp_mod.bluetooth = mock_bt
        with patch.dict("sys.modules", {"homeassistant.components.bluetooth": mock_bt}):
            self.assertTrue(is_bluetooth_available(mock_hass))

    async def test_step_user_without_bluetooth(self):
        """Test initial step when Bluetooth is not available."""
        flow = PassiveDeviceTrackerConfigFlow()
        flow.hass = MagicMock()

        with patch("custom_components.passive_device_tracker.config_flow.is_bluetooth_available", return_value=False):
            result = await flow.async_step_user()
            self.assertEqual(result["type"], "form")
            self.assertEqual(result["step_id"], "user")

            result2 = await flow.async_step_user({
                CONF_NAME: "Office Laptop",
                CONF_INTERFACES: [INTERFACE_LAN],
            })
            self.assertEqual(result2["type"], "form")
            self.assertEqual(result2["step_id"], "configure")

    async def test_step_configure_lan_success(self):
        """Test configuring LAN interface successfully."""
        flow = PassiveDeviceTrackerConfigFlow()
        flow.hass = MagicMock()
        flow._device_name = "Workstation"
        flow._selected_interfaces = [INTERFACE_LAN]
        flow.async_set_unique_id = AsyncMock()
        flow._abort_if_unique_id_configured = MagicMock()

        result = await flow.async_step_configure({
            CONF_LAN_IP: "192.168.2.150",
            CONF_LAN_MAC: "AA:BB:CC:DD:EE:01",
            CONF_CONSIDER_HOME: 180,
        })

        self.assertEqual(result["type"], "create_entry")
        self.assertEqual(result["title"], "Workstation")
        self.assertEqual(result["data"][CONF_LAN_IP], "192.168.2.150")
        self.assertEqual(result["data"][CONF_LAN_MAC], "aa:bb:cc:dd:ee:01")

    async def test_step_configure_invalid_mac(self):
        """Test configuring with invalid MAC address format."""
        flow = PassiveDeviceTrackerConfigFlow()
        flow.hass = MagicMock()
        flow._device_name = "Bad Device"
        flow._selected_interfaces = [INTERFACE_LAN]

        result = await flow.async_step_configure({
            CONF_LAN_MAC: "not-a-mac",
        })

        self.assertEqual(result["type"], "form")
        self.assertEqual(result["errors"][CONF_LAN_MAC], "invalid_mac")

    async def test_step_configure_missing_lan_credentials(self):
        """Test configuring LAN without both IP and MAC."""
        flow = PassiveDeviceTrackerConfigFlow()
        flow.hass = MagicMock()
        flow._device_name = "Empty LAN"
        flow._selected_interfaces = [INTERFACE_LAN]

        result = await flow.async_step_configure({
            CONF_LAN_IP: "",
            CONF_LAN_MAC: "",
        })

        self.assertEqual(result["type"], "form")
        self.assertEqual(result["errors"]["base"], "missing_lan_credentials")


if __name__ == "__main__":
    unittest.main()
