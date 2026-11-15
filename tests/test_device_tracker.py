"""Tests for device_tracker platform and entity state."""

from datetime import datetime, timedelta, timezone
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

import tests.ha_mock  # noqa: F401

from custom_components.passive_device_tracker.const import (
    DOMAIN,
    CONF_INTERFACES,
    INTERFACE_LAN,
    INTERFACE_WLAN,
    INTERFACE_BLUETOOTH,
    CONF_LAN_IP,
    CONF_LAN_MAC,
    CONF_WLAN_IP,
    CONF_BT_MAC,
    CONF_CONSIDER_HOME,
    CONF_PING_INTERVAL,
)
from custom_components.passive_device_tracker.device_tracker import (
    PassiveDeviceTrackerEntity,
)


class TestDeviceTracker(unittest.IsolatedAsyncioTestCase):
    """Test passive_device_tracker entity."""

    def setUp(self):
        """Set up test entry and entity."""
        self.entry = MagicMock()
        self.entry.entry_id = "test_entry_456"
        self.entry.title = "Omni Laptop"
        self.entry.data = {
            CONF_INTERFACES: [INTERFACE_LAN, INTERFACE_WLAN, INTERFACE_BLUETOOTH],
            CONF_LAN_IP: "192.168.2.10",
            CONF_LAN_MAC: "aa:bb:cc:dd:ee:01",
            CONF_WLAN_IP: "192.168.2.20",
            CONF_BT_MAC: "11:22:33:44:55:66",
            CONF_CONSIDER_HOME: 180,
            CONF_PING_INTERVAL: 30,
        }
        self.entry.options = {}
        self.entity = PassiveDeviceTrackerEntity(self.entry)
        self.entity.hass = MagicMock()
        self.entity.async_write_ha_state = MagicMock()

    def test_initial_state(self):
        """Test initial disconnected state."""
        self.assertFalse(self.entity.is_connected)
        self.assertIsNone(self.entity.extra_state_attributes.get("last_seen_by"))

    def test_lan_activity_marks_home(self):
        """Test that LAN activity marks device home."""
        now = datetime.now(timezone.utc)
        self.entity._update_seen("lan", now, latency=5.2)

        self.assertTrue(self.entity.is_connected)
        self.assertEqual(self.entity.source_type, "router")
        attrs = self.entity.extra_state_attributes
        self.assertEqual(attrs["last_seen_by"], "lan")
        self.assertTrue(attrs["lan_status"])
        self.assertEqual(attrs["lan_latency_ms"], 5.2)

    def test_multi_interface_roaming(self):
        """Test seamless roaming from LAN to WLAN."""
        t1 = datetime.now(timezone.utc) - timedelta(seconds=60)
        self.entity._update_seen("lan", t1, latency=2.0)
        self.assertEqual(self.entity.extra_state_attributes["last_seen_by"], "lan")

        # Laptop unplugged, now detected on WLAN
        t2 = datetime.now(timezone.utc)
        self.entity._update_seen("wlan", t2, latency=15.0)

        self.assertTrue(self.entity.is_connected)
        self.assertEqual(self.entity.extra_state_attributes["last_seen_by"], "wlan")
        self.assertTrue(self.entity.extra_state_attributes["wlan_status"])

    def test_bluetooth_activity_updates_source_type(self):
        """Test that Bluetooth detection sets BLUETOOTH_LE source type."""
        now = datetime.now(timezone.utc)
        self.entity._update_seen("bluetooth", now, rssi=-65)

        self.assertTrue(self.entity.is_connected)
        self.assertEqual(self.entity.source_type, "bluetooth_le")
        self.assertEqual(self.entity.extra_state_attributes["last_seen_by"], "bluetooth")
        self.assertEqual(self.entity.extra_state_attributes["bluetooth_rssi"], -65)

    def test_consider_home_expiration(self):
        """Test that device transitions to not_home after consider_home expires."""
        old_time = datetime.now(timezone.utc) - timedelta(seconds=200)
        self.entity._update_seen("lan", old_time)

        # consider_home is 180s, 200s has elapsed -> should be not connected (not_home)
        self.assertFalse(self.entity.is_connected)


if __name__ == "__main__":
    unittest.main()
