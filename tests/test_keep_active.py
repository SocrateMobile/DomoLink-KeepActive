"""Comprehensive unit tests for DomoLink KeepActive custom component."""
import asyncio
import os
import sys
import types
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

# Provide mock homeassistant modules if not installed in current environment
if "homeassistant" not in sys.modules:
    def make_pkg(name):
        mod = types.ModuleType(name)
        mod.__path__ = []
        sys.modules[name] = mod
        return mod

    ha = make_pkg("homeassistant")
    ha_const = make_pkg("homeassistant.const")
    ha_const.STATE_ON = "on"
    ha_const.STATE_OFF = "off"
    ha_const.STATE_UNAVAILABLE = "unavailable"
    ha_const.STATE_UNKNOWN = "unknown"
    ha_const.ATTR_DEVICE_CLASS = "device_class"
    ha_const.ATTR_ICON = "icon"
    ha_const.ATTR_UNIT_OF_MEASUREMENT = "unit_of_measurement"
    ha_const.ATTR_ENTITY_ID = "entity_id"
    ha_const.SERVICE_TURN_ON = "turn_on"
    ha_const.SERVICE_TURN_OFF = "turn_off"

    class Platform:
        BINARY_SENSOR = "binary_sensor"
        SENSOR = "sensor"
        SWITCH = "switch"

    ha_const.Platform = Platform

    ha_core = make_pkg("homeassistant.core")
    ha_core.callback = lambda f: f
    ha_core.HomeAssistant = MagicMock
    ha_core.Event = MagicMock
    ha_core.CALLBACK_TYPE = Any = object

    class MockEntity:
        def __init__(self, *args, **kwargs):
            self.hass = MagicMock()
            self.entity_id = "binary_sensor.test_proxy"
            self._attr_is_on = False
            self._attr_available = True
            self._attr_device_class = None
            self._attr_icon = None
            self._attr_native_value = None
            self._attr_native_unit_of_measurement = None

        def async_write_ha_state(self):
            pass

        async def async_added_to_hass(self):
            pass

        async def async_will_remove_from_hass(self):
            pass

        async def async_get_last_state(self):
            return None

    ha_helpers = make_pkg("homeassistant.helpers")
    ha_restore = make_pkg("homeassistant.helpers.restore_state")
    ha_restore.RestoreEntity = MockEntity

    ha_event = make_pkg("homeassistant.helpers.event")
    ha_event.async_call_later = MagicMock(return_value=lambda: None)
    ha_event.async_track_state_change_event = MagicMock(return_value=lambda: None)

    ha_ep = make_pkg("homeassistant.helpers.entity_platform")
    ha_ep.AddEntitiesCallback = MagicMock

    ha_bs = make_pkg("homeassistant.components.binary_sensor")
    ha_bs.BinarySensorEntity = MockEntity

    ha_s = make_pkg("homeassistant.components.sensor")
    ha_s.SensorEntity = MockEntity

    ha_sw = make_pkg("homeassistant.components.switch")
    ha_sw.SwitchEntity = MockEntity

    ha_cf = make_pkg("homeassistant.config_entries")
    ha_cf.ConfigEntry = MagicMock
    class MockConfigFlow:
        def __init_subclass__(cls, **kwargs):
            pass
    ha_cf.ConfigFlow = MockConfigFlow
    ha_cf.OptionsFlow = MockConfigFlow

    ha_sel = make_pkg("homeassistant.helpers.selector")
    class DummySelector:
        def __init__(self, *args, **kwargs):
            pass
    ha_sel.EntitySelector = DummySelector
    ha_sel.EntitySelectorConfig = DummySelector
    ha_sel.TextSelector = DummySelector
    ha_sel.NumberSelector = DummySelector
    ha_sel.NumberSelectorConfig = DummySelector
    class NumberSelectorMode:
        BOX = "box"
    ha_sel.NumberSelectorMode = NumberSelectorMode
    ha_sel.BooleanSelector = DummySelector

    ha_def = make_pkg("homeassistant.data_entry_flow")
    ha_def.FlowResult = dict

if "voluptuous" not in sys.modules:
    vol_mock = types.ModuleType("voluptuous")
    vol_mock.__path__ = []
    vol_mock.Schema = lambda s: s
    vol_mock.Optional = lambda k, **kw: k
    vol_mock.Required = lambda k, **kw: k
    sys.modules["voluptuous"] = vol_mock

# Add custom_components directory to path
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, repo_root)

from custom_components.domolink_keep_active.const import (
    CONF_GRACE_PERIOD,
    CONF_HOLD_DURATION,
    CONF_OPTIMISTIC,
    CONF_SOURCE_ENTITY,
    DEFAULT_GRACE_PERIOD,
    DEFAULT_HOLD_DURATION,
    DOMAIN,
)
from custom_components.domolink_keep_active.entity import KeepActiveBaseEntity
from custom_components.domolink_keep_active.binary_sensor import KeepActiveBinarySensor
from custom_components.domolink_keep_active.sensor import KeepActiveSensor
from custom_components.domolink_keep_active.switch import KeepActiveSwitch
from custom_components.domolink_keep_active.config_flow import DomoLinkKeepActiveConfigFlow, get_platform_from_entity


class TestDomoLinkKeepActive(unittest.TestCase):
    """Test suite for KeepActive entity logic and platforms."""

    def setUp(self):
        self.hass = MagicMock()
        self.entry_id = "test_entry_123"
        self.config = {
            CONF_SOURCE_ENTITY: "binary_sensor.mouvement_zigbee",
            CONF_HOLD_DURATION: 15,
            CONF_GRACE_PERIOD: 30,
            CONF_OPTIMISTIC: True,
        }

    def test_get_platform_from_entity(self):
        """Verify correct platform detection from entity domain."""
        self.assertEqual(get_platform_from_entity("binary_sensor.motion"), "binary_sensor")
        self.assertEqual(get_platform_from_entity("sensor.temperature"), "sensor")
        self.assertEqual(get_platform_from_entity("switch.plug"), "switch")
        self.assertEqual(get_platform_from_entity("unknown.device"), "binary_sensor")

    def test_binary_sensor_turns_on_immediately(self):
        """When source becomes ON, proxy immediately turns ON and cancels any hold."""
        sensor = KeepActiveBinarySensor(self.entry_id, self.config)
        sensor.hass = self.hass

        # Simulate source turning ON
        sensor._handle_new_source_state("on", {})
        self.assertTrue(sensor._attr_is_on)
        self.assertTrue(sensor._attr_available)
        self.assertIsNone(sensor._timer_hold)

    def test_binary_sensor_holds_active_on_off(self):
        """When source turns OFF, proxy stays ON and schedules hold timer."""
        timers = []
        def fake_call_later(hass, delay, callback):
            timers.append((delay, callback))
            return lambda: timers.clear()

        with patch("custom_components.domolink_keep_active.binary_sensor.async_call_later", side_effect=fake_call_later):
            sensor = KeepActiveBinarySensor(self.entry_id, self.config)
            sensor.hass = self.hass

            # First turn ON
            sensor._handle_new_source_state("on", {})
            self.assertTrue(sensor._attr_is_on)

            # Then turn OFF
            sensor._handle_new_source_state("off", {})
            self.assertTrue(sensor._attr_is_on)  # Must still be ON!
            self.assertEqual(len(timers), 1)
            self.assertEqual(timers[0][0], 15)  # 15s hold delay

            # Simulate expiration
            callback = timers[0][1]
            sensor._async_hold_expired(None)
            self.assertFalse(sensor._attr_is_on)  # Now turned OFF

    def test_unavailable_grace_period(self):
        """When source becomes unavailable, proxy remains available during grace period."""
        timers = []
        def fake_call_later(hass, delay, callback):
            timers.append((delay, callback))
            return lambda: timers.clear()

        with patch("custom_components.domolink_keep_active.entity.async_call_later", side_effect=fake_call_later):
            sensor = KeepActiveBinarySensor(self.entry_id, self.config)
            sensor.hass = self.hass
            sensor._attr_is_on = True

            # Source disconnects during Zigbee update / mesh hop
            sensor._handle_new_source_state("unavailable", {})
            self.assertTrue(sensor._attr_available)  # Still available due to grace period!
            self.assertTrue(sensor._attr_is_on)
            self.assertEqual(len(timers), 1)
            self.assertEqual(timers[0][0], 30)  # 30s grace delay

            # If device recovers before expiration
            sensor._handle_new_source_state("on", {})
            self.assertTrue(sensor._attr_available)
            self.assertIsNone(sensor._timer_grace)

    def test_unavailable_grace_period_expired(self):
        """If source stays unavailable after grace period expires, proxy becomes unavailable."""
        sensor = KeepActiveBinarySensor(self.entry_id, self.config)
        sensor.hass = self.hass
        sensor._attr_available = True

        sensor._async_grace_expired(None)
        self.assertFalse(sensor._attr_available)

    def test_sensor_updates_value_and_unit(self):
        """Sensor proxy mirrors value and unit of measurement."""
        sensor_config = {
            CONF_SOURCE_ENTITY: "sensor.zigbee_temp",
            CONF_HOLD_DURATION: 0,
            CONF_GRACE_PERIOD: 45,
        }
        sensor = KeepActiveSensor(self.entry_id, sensor_config)
        sensor.hass = self.hass

        sensor._handle_new_source_state("21.5", {"unit_of_measurement": "°C", "state_class": "measurement"})
        self.assertEqual(sensor._attr_native_value, "21.5")
        self.assertEqual(sensor._attr_native_unit_of_measurement, "°C")

    def test_switch_optimistic_forwarding(self):
        """Switch optimistic toggle immediately reflects state and forwards HA service call."""
        switch_config = {
            CONF_SOURCE_ENTITY: "switch.prise_zigbee",
            CONF_HOLD_DURATION: 0,
            CONF_GRACE_PERIOD: 60,
            CONF_OPTIMISTIC: True,
        }
        switch = KeepActiveSwitch(self.entry_id, switch_config)
        switch.hass = self.hass
        switch.hass.services.async_call = AsyncMock()

        # Call async_turn_on
        asyncio.run(switch.async_turn_on())
        self.assertTrue(switch._attr_is_on)
        switch.hass.services.async_call.assert_called_with(
            "homeassistant",
            "turn_on",
            {"entity_id": "switch.prise_zigbee"},
            blocking=False,
        )

        # Call async_turn_off
        asyncio.run(switch.async_turn_off())
        self.assertFalse(switch._attr_is_on)
        switch.hass.services.async_call.assert_called_with(
            "homeassistant",
            "turn_off",
            {"entity_id": "switch.prise_zigbee"},
            blocking=False,
        )

    def test_binary_sensor_re_turn_on_cancels_hold(self):
        """If source turns back ON while hold timer is active, timer is canceled and state remains ON."""
        sensor = KeepActiveBinarySensor(self.entry_id, self.config)
        sensor.hass = self.hass
        sensor._attr_is_on = True
        fake_cancel = MagicMock()
        sensor._timer_hold = fake_cancel

        sensor._handle_new_source_state("on", {})
        self.assertTrue(sensor._attr_is_on)
        fake_cancel.assert_called_once()
        self.assertIsNone(sensor._timer_hold)

    def test_restore_state_binary_sensor(self):
        """Verify restored state initialization."""
        sensor = KeepActiveBinarySensor(self.entry_id, self.config)
        sensor._handle_restored_state("on", {})
        self.assertTrue(sensor._attr_is_on)

        sensor._handle_restored_state("off", {})
        self.assertFalse(sensor._attr_is_on)

    def test_config_flow_validation(self):
        """Config flow rejects unsupported domain and accepts valid ones."""
        flow = DomoLinkKeepActiveConfigFlow()
        flow.hass = self.hass
        flow.async_set_unique_id = AsyncMock()
        flow._abort_if_unique_id_configured = MagicMock()
        flow.async_create_entry = MagicMock(return_value={"type": "create_entry"})
        flow.async_show_form = MagicMock(return_value={"type": "form"})

        # Unsupported domain
        result_err = asyncio.run(flow.async_step_user({
            CONF_SOURCE_ENTITY: "camera.salon",
        }))
        flow.async_show_form.assert_called()
        self.assertEqual(flow.async_show_form.call_args[1]["errors"]["base"], "unsupported_domain")

        # Valid domain
        result_ok = asyncio.run(flow.async_step_user({
            CONF_SOURCE_ENTITY: "binary_sensor.porte",
            CONF_HOLD_DURATION: 20,
            CONF_GRACE_PERIOD: 40,
        }))
        flow.async_create_entry.assert_called_once()


if __name__ == "__main__":
    unittest.main()
