"""Centralized Home Assistant stubbing for local unit tests."""

import sys
import types
from typing import Any
from unittest.mock import AsyncMock, MagicMock


def install_ha_mocks() -> None:
    """Install Home Assistant mocks into sys.modules if not already present."""
    if "homeassistant" in sys.modules and hasattr(sys.modules["homeassistant"], "__path__"):
        return

    ha_mod = types.ModuleType("homeassistant")
    ha_mod.__path__ = []

    core_mod = types.ModuleType("homeassistant.core")
    core_mod.HomeAssistant = MagicMock
    core_mod.callback = lambda fn: fn

    const_mod = types.ModuleType("homeassistant.const")
    class Platform:
        DEVICE_TRACKER = "device_tracker"
        SENSOR = "sensor"
        BINARY_SENSOR = "binary_sensor"
    const_mod.Platform = Platform
    const_mod.STATE_HOME = "home"
    const_mod.STATE_NOT_HOME = "not_home"

    config_entries_mod = types.ModuleType("homeassistant.config_entries")
    class ConfigFlow:
        def __init_subclass__(cls, **kwargs: Any) -> None:
            pass
        def async_show_form(self, **kwargs):
            return {"type": "form", **kwargs}
        def async_create_entry(self, **kwargs):
            return {"type": "create_entry", **kwargs}
        def async_abort(self, **kwargs):
            return {"type": "abort", **kwargs}

    class OptionsFlow:
        def __init_subclass__(cls, **kwargs: Any) -> None:
            pass
        def async_show_form(self, **kwargs):
            return {"type": "form", **kwargs}
        def async_create_entry(self, **kwargs):
            return {"type": "create_entry", **kwargs}

    config_entries_mod.ConfigFlow = ConfigFlow
    config_entries_mod.OptionsFlow = OptionsFlow
    config_entries_mod.ConfigEntry = MagicMock

    data_entry_flow_mod = types.ModuleType("homeassistant.data_entry_flow")
    data_entry_flow_mod.FlowResult = dict[str, Any]

    helpers_mod = types.ModuleType("homeassistant.helpers")
    helpers_mod.__path__ = []

    cv_mod = types.ModuleType("homeassistant.helpers.config_validation")
    cv_mod.multi_select = lambda options: lambda val: val
    cv_mod.string = str
    cv_mod.boolean = bool

    dr_mod = types.ModuleType("homeassistant.helpers.device_registry")
    dr_mod.CONNECTION_NETWORK_MAC = "mac"
    dr_mod.CONNECTION_BLUETOOTH = "bluetooth"
    dr_mod.async_get = MagicMock()

    device_tracker_mod = types.ModuleType("homeassistant.components.device_tracker")
    class SourceType:
        ROUTER = "router"
        BLUETOOTH_LE = "bluetooth_le"
    class TrackerEntity:
        hass = None
        entity_id = None
        _attr_name = None
        _attr_unique_id = None
        _attr_device_info = None
        _attr_extra_state_attributes = {}
        async def async_write_ha_state(self):
            pass
    device_tracker_mod.SourceType = SourceType
    device_tracker_mod.TrackerEntity = TrackerEntity

    components_mod = types.ModuleType("homeassistant.components")
    components_mod.__path__ = []
    components_mod.device_tracker = device_tracker_mod

    sys.modules["homeassistant"] = ha_mod
    sys.modules["homeassistant.core"] = core_mod
    sys.modules["homeassistant.const"] = const_mod
    sys.modules["homeassistant.config_entries"] = config_entries_mod
    sys.modules["homeassistant.data_entry_flow"] = data_entry_flow_mod
    sys.modules["homeassistant.helpers"] = helpers_mod
    sys.modules["homeassistant.helpers.config_validation"] = cv_mod
    sys.modules["homeassistant.helpers.device_registry"] = dr_mod
    sys.modules["homeassistant.components"] = components_mod
    sys.modules["homeassistant.components.device_tracker"] = device_tracker_mod


install_ha_mocks()
