"""Tests for __init__ lifecycle and device registry."""

import unittest
from unittest.mock import AsyncMock, MagicMock, patch

import tests.ha_mock  # noqa: F401

from custom_components.passive_device_tracker import (
    async_setup_entry,
    async_unload_entry,
)
from custom_components.passive_device_tracker.const import (
    DOMAIN,
    MANUFACTURER,
    DEFAULT_MODEL,
    CONF_LAN_MAC,
    CONF_BT_MAC,
)


class TestInit(unittest.IsolatedAsyncioTestCase):
    """Test passive_device_tracker lifecycle."""

    async def test_setup_and_device_registry(self):
        """Test device registry creation with Omni Consumer Products."""
        mock_hass = MagicMock()
        mock_hass.data = {}
        mock_hass.config_entries.async_forward_entry_setups = AsyncMock(return_value=True)

        mock_entry = MagicMock()
        mock_entry.entry_id = "test_entry_123"
        mock_entry.title = "Omni RoboLaptop"
        mock_entry.data = {
            CONF_LAN_MAC: "aa:bb:cc:dd:ee:01",
            CONF_BT_MAC: "11:22:33:44:55:66",
        }
        mock_entry.options = {}

        mock_dr = MagicMock()
        with patch("homeassistant.helpers.device_registry.async_get", return_value=mock_dr):
            result = await async_setup_entry(mock_hass, mock_entry)
            self.assertTrue(result)

            # Verify device registry registration with Omni Consumer Products
            mock_dr.async_get_or_create.assert_called_once()
            call_kwargs = mock_dr.async_get_or_create.call_args.kwargs
            self.assertEqual(call_kwargs["name"], "Omni RoboLaptop")
            self.assertEqual(call_kwargs["manufacturer"], "Omni Consumer Products")
            self.assertEqual(call_kwargs["model"], DEFAULT_MODEL)
            self.assertIn(("mac", "aa:bb:cc:dd:ee:01"), call_kwargs["connections"])
            self.assertIn(("bluetooth", "11:22:33:44:55:66"), call_kwargs["connections"])

    async def test_unload_entry(self):
        """Test unloading entry cleanly."""
        mock_hass = MagicMock()
        mock_hass.data = {DOMAIN: {"entry_1": {}}}
        mock_hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)

        mock_entry = MagicMock()
        mock_entry.entry_id = "entry_1"

        result = await async_unload_entry(mock_hass, mock_entry)
        self.assertTrue(result)
        self.assertNotIn("entry_1", mock_hass.data[DOMAIN])


if __name__ == "__main__":
    unittest.main()
