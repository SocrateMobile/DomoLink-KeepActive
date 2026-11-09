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

    ha_dr = make_pkg("homeassistant.helpers.device_registry")
    class DeviceEntryType:
        SERVICE = "service"
    ha_dr.DeviceEntryType = DeviceEntryType
    ha_dr.DeviceInfo = lambda **kw: kw
    ha_dr.async_get = MagicMock()

    ha_er = make_pkg("homeassistant.helpers.entity_registry")
    ha_er.async_get = MagicMock()

    ha_components = make_pkg("homeassistant.components")
    ha_frontend = make_pkg("homeassistant.components.frontend")
    ha_components.frontend = ha_frontend
    ha_frontend.async_register_built_in_panel = MagicMock()
    ha_frontend.async_remove_panel = MagicMock()
    ha_frontend.add_extra_js_url = MagicMock()

    ha_http = make_pkg("homeassistant.components.http")
    ha_components.http = ha_http
    class HomeAssistantView:
        requires_auth = True
        def json(self, data, status=200):
            return {"data": data, "status": status}
    ha_http.HomeAssistantView = HomeAssistantView

    ha_exc = make_pkg("homeassistant.exceptions")
    class Unauthorized(Exception):
        pass
    ha_exc.Unauthorized = Unauthorized

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
        SLIDER = "slider"
    ha_sel.NumberSelectorMode = NumberSelectorMode
    ha_sel.BooleanSelector = DummySelector
    ha_sel.SelectSelector = DummySelector
    ha_sel.SelectSelectorConfig = DummySelector
    ha_sel.SelectOptionDict = lambda **kw: kw
    class SelectSelectorMode:
        LIST = "list"
        DROPDOWN = "dropdown"
    ha_sel.SelectSelectorMode = SelectSelectorMode

    ha_def = make_pkg("homeassistant.data_entry_flow")
    ha_def.FlowResult = dict

if "aiohttp" not in sys.modules:
    aiohttp_mock = types.ModuleType("aiohttp")
    aiohttp_web_mock = types.ModuleType("aiohttp.web")
    aiohttp_web_mock.Request = MagicMock
    aiohttp_web_mock.Response = MagicMock
    aiohttp_mock.web = aiohttp_web_mock
    sys.modules["aiohttp"] = aiohttp_mock
    sys.modules["aiohttp.web"] = aiohttp_web_mock

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
    ACTION_ADD,
    ACTION_DELETE,
    ACTION_EDIT,
    ACTION_VIEW,
    CONF_AUTO_OTA_TRIGGER,
    CONF_GRACE_PERIOD,
    CONF_HOLD_DURATION,
    CONF_NAME,
    CONF_OPTIMISTIC,
    CONF_OTA_DURATION,
    CONF_PING_INTERVAL,
    CONF_PING_METHOD,
    CONF_RULES,
    CONF_RULE_ID,
    CONF_SOURCE_ENTITY,
    DEFAULT_AUTO_OTA_TRIGGER,
    DEFAULT_GRACE_PERIOD,
    DEFAULT_HOLD_DURATION,
    DEFAULT_OPTIMISTIC,
    DEFAULT_OTA_DURATION,
    DEFAULT_PING_INTERVAL,
    DEFAULT_PING_METHOD,
    DOMAIN,
    MAX_OTA_DURATION,
    MAX_PING_INTERVAL,
    MIN_OTA_DURATION,
    MIN_PING_INTERVAL,
)
from custom_components.domolink_keep_active.entity import KeepActiveBaseEntity
from custom_components.domolink_keep_active.binary_sensor import (
    KeepActiveBinarySensor,
    async_setup_entry as bs_async_setup_entry,
)
from custom_components.domolink_keep_active.sensor import (
    KeepActiveSensor,
    async_setup_entry as s_async_setup_entry,
)
from custom_components.domolink_keep_active.switch import (
    KeepActiveSwitch,
    async_setup_entry as sw_async_setup_entry,
)
from custom_components.domolink_keep_active.helpers import (
    get_platform_from_entity,
    get_rules_from_entry,
    normalize_ota_duration,
    normalize_ping_interval,
)
from custom_components.domolink_keep_active.config_flow import (
    DomoLinkKeepActiveConfigFlow,
    DomoLinkKeepActiveOptionsFlowHandler,
)
from custom_components.domolink_keep_active.ota_manager import OtaKeepAwakeManager
from custom_components.domolink_keep_active.api import DomolinkKeepActiveApiView


class TestDomoLinkKeepActive(unittest.TestCase):
    """Test suite for KeepActive entity logic, platforms, CRUD options flow, and OTA engine."""

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

    def test_normalize_ota_sliders(self):
        """Verify OTA duration (10-90) and ping interval (1-60) are properly clamped."""
        self.assertEqual(normalize_ota_duration(5), MIN_OTA_DURATION)
        self.assertEqual(normalize_ota_duration(120), MAX_OTA_DURATION)
        self.assertEqual(normalize_ota_duration(45), 45)
        self.assertEqual(normalize_ota_duration("invalid"), DEFAULT_OTA_DURATION)

        self.assertEqual(normalize_ping_interval(0), MIN_PING_INTERVAL)
        self.assertEqual(normalize_ping_interval(100), MAX_PING_INTERVAL)
        self.assertEqual(normalize_ping_interval(15), 15)
        self.assertEqual(normalize_ping_interval("invalid"), DEFAULT_PING_INTERVAL)

    def test_device_info_attached(self):
        """Verify device_info is attached to KeepActiveBaseEntity so entities group under DomoLink."""
        sensor = KeepActiveBinarySensor(self.entry_id, self.config)
        self.assertIsNotNone(sensor._attr_device_info)
        self.assertEqual(sensor._attr_device_info.get("name"), "DomoLink KeepActive")
        self.assertEqual(sensor._attr_device_info.get("identifiers"), {(DOMAIN, self.entry_id)})

    def test_get_rules_from_entry_v1_compatibility(self):
        """Verify seamless backward compatibility with v1.0.0 entries having only data[CONF_SOURCE_ENTITY]."""
        entry = MagicMock()
        entry.data = {
            CONF_SOURCE_ENTITY: "binary_sensor.radar_salon",
            CONF_NAME: "KeepActive Salon",
            CONF_HOLD_DURATION: 45,
            CONF_GRACE_PERIOD: 90,
            CONF_OPTIMISTIC: True,
        }
        entry.options = {}

        rules = get_rules_from_entry(entry)
        self.assertEqual(len(rules), 1)
        self.assertEqual(rules[0][CONF_SOURCE_ENTITY], "binary_sensor.radar_salon")
        self.assertEqual(rules[0][CONF_NAME], "KeepActive Salon")
        self.assertEqual(rules[0][CONF_HOLD_DURATION], 45)
        self.assertEqual(rules[0][CONF_GRACE_PERIOD], 90)
        self.assertTrue(rules[0][CONF_OPTIMISTIC])
        self.assertEqual(rules[0][CONF_OTA_DURATION], DEFAULT_OTA_DURATION)
        self.assertEqual(rules[0][CONF_PING_INTERVAL], DEFAULT_PING_INTERVAL)

    def test_get_rules_from_entry_multi_rules(self):
        """Verify get_rules_from_entry returns full list from options with OTA defaults."""
        entry = MagicMock()
        entry.data = {}
        entry.options = {
            CONF_RULES: [
                {CONF_SOURCE_ENTITY: "binary_sensor.radar_1", CONF_NAME: "Radar 1", CONF_OTA_DURATION: 40},
                {CONF_SOURCE_ENTITY: "switch.prise_1", CONF_NAME: "Prise 1", CONF_PING_INTERVAL: 10},
            ]
        }
        rules = get_rules_from_entry(entry)
        self.assertEqual(len(rules), 2)
        self.assertEqual(rules[0][CONF_SOURCE_ENTITY], "binary_sensor.radar_1")
        self.assertEqual(rules[0][CONF_OTA_DURATION], 40)
        self.assertEqual(rules[1][CONF_SOURCE_ENTITY], "switch.prise_1")
        self.assertEqual(rules[1][CONF_PING_INTERVAL], 10)

    def test_platform_setup_entries(self):
        """Verify that platform async_setup_entry correctly instantiates only its matching entities."""
        entry = MagicMock()
        entry.entry_id = "test_entry_multi"
        entry.data = {}
        entry.options = {
            CONF_RULES: [
                {CONF_SOURCE_ENTITY: "binary_sensor.motion", CONF_NAME: "Motion"},
                {CONF_SOURCE_ENTITY: "sensor.temp", CONF_NAME: "Temp"},
                {CONF_SOURCE_ENTITY: "switch.relay", CONF_NAME: "Relay"},
            ]
        }

        # Binary sensor platform
        bs_added = []
        asyncio.run(bs_async_setup_entry(self.hass, entry, lambda entities, update: bs_added.extend(entities)))
        self.assertEqual(len(bs_added), 1)
        self.assertIsInstance(bs_added[0], KeepActiveBinarySensor)

        # Sensor platform
        s_added = []
        asyncio.run(s_async_setup_entry(self.hass, entry, lambda entities, update: s_added.extend(entities)))
        self.assertEqual(len(s_added), 1)
        self.assertIsInstance(s_added[0], KeepActiveSensor)

        # Switch platform
        sw_added = []
        asyncio.run(sw_async_setup_entry(self.hass, entry, lambda entities, update: sw_added.extend(entities)))
        self.assertEqual(len(sw_added), 1)
        self.assertIsInstance(sw_added[0], KeepActiveSwitch)

    def test_binary_sensor_turns_on_immediately(self):
        """When source becomes ON, proxy immediately turns ON and cancels any hold."""
        sensor = KeepActiveBinarySensor(self.entry_id, self.config)
        sensor.hass = self.hass

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

            sensor._handle_new_source_state("on", {})
            self.assertTrue(sensor._attr_is_on)

            sensor._handle_new_source_state("off", {})
            self.assertTrue(sensor._attr_is_on)
            self.assertEqual(len(timers), 1)
            self.assertEqual(timers[0][0], 15)

            sensor._async_hold_expired(None)
            self.assertFalse(sensor._attr_is_on)

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

            sensor._handle_new_source_state("unavailable", {})
            self.assertTrue(sensor._attr_available)
            self.assertTrue(sensor._attr_is_on)
            self.assertEqual(len(timers), 1)
            self.assertEqual(timers[0][0], 30)

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

        asyncio.run(switch.async_turn_on())
        self.assertTrue(switch._attr_is_on)
        switch.hass.services.async_call.assert_called_with(
            "homeassistant",
            "turn_on",
            {"entity_id": "switch.prise_zigbee"},
            blocking=False,
        )

        asyncio.run(switch.async_turn_off())
        self.assertFalse(switch._attr_is_on)
        switch.hass.services.async_call.assert_called_with(
            "homeassistant",
            "turn_off",
            {"entity_id": "switch.prise_zigbee"},
            blocking=False,
        )

    def test_config_flow_validation(self):
        """Config flow rejects unsupported domain and accepts valid ones with OTA fields."""
        flow = DomoLinkKeepActiveConfigFlow()
        flow.hass = self.hass
        flow.async_set_unique_id = AsyncMock()
        flow._abort_if_unique_id_configured = MagicMock()
        flow.async_create_entry = MagicMock(return_value={"type": "create_entry"})
        flow.async_show_form = MagicMock(return_value={"type": "form"})

        # Unsupported domain
        asyncio.run(flow.async_step_user({
            CONF_SOURCE_ENTITY: "camera.salon",
        }))
        flow.async_show_form.assert_called()
        self.assertEqual(flow.async_show_form.call_args[1]["errors"]["base"], "unsupported_domain")

        # Valid domain with OTA duration slider
        asyncio.run(flow.async_step_user({
            CONF_SOURCE_ENTITY: "binary_sensor.porte",
            CONF_HOLD_DURATION: 20,
            CONF_GRACE_PERIOD: 40,
            CONF_OTA_DURATION: 45,
            CONF_PING_INTERVAL: 8,
        }))
        flow.async_create_entry.assert_called_once()
        created_data = flow.async_create_entry.call_args[1]["data"]
        self.assertEqual(created_data[CONF_RULES][0][CONF_OTA_DURATION], 45)
        self.assertEqual(created_data[CONF_RULES][0][CONF_PING_INTERVAL], 8)

    def test_ota_manager_lifecycle(self):
        """Test OTA keep-awake start, pinging, and stopping."""
        ota = OtaKeepAwakeManager(self.hass)
        self.hass.services.has_service = MagicMock(return_value=True)
        self.hass.services.async_call = AsyncMock()

        # Start OTA session for 30 minutes, 5s interval
        asyncio.run(ota.async_start_ota("binary_sensor.radar", duration_minutes=30, ping_interval=5))

        state = ota.get_session_state("binary_sensor.radar")
        self.assertTrue(state["active"])
        self.assertEqual(state["duration_minutes"], 30)
        self.assertEqual(state["ping_interval"], 5)
        self.assertGreaterEqual(state["ping_count"], 1)

        # Stop session
        ota.async_stop_ota("binary_sensor.radar", reason="test")
        state_after = ota.get_session_state("binary_sensor.radar")
        self.assertFalse(state_after["active"])

        # Check logs
        logs = ota.get_logs()
        self.assertGreaterEqual(len(logs), 2)
        self.assertIn("Mode OTA Keep-Awake", logs[-1]["message"] if logs else "")

    def test_api_view_endpoints(self):
        """Test DomolinkKeepActiveApiView GET and POST endpoints."""
        ota = OtaKeepAwakeManager(self.hass)
        self.hass.services.has_service = MagicMock(return_value=True)
        self.hass.services.async_call = AsyncMock()
        self.hass.states.async_all = MagicMock(return_value=[])

        # Mock active entry
        entry = MagicMock()
        entry.entry_id = "entry_1"
        entry.data = {}
        entry.options = {
            CONF_RULES: [
                {
                    CONF_RULE_ID: "binary_sensor.radar",
                    CONF_SOURCE_ENTITY: "binary_sensor.radar",
                    CONF_NAME: "Radar",
                    CONF_HOLD_DURATION: 30,
                    CONF_GRACE_PERIOD: 60,
                    CONF_OPTIMISTIC: True,
                    CONF_OTA_DURATION: 30,
                    CONF_PING_INTERVAL: 5,
                }
            ]
        }
        self.hass.config_entries.async_entries = MagicMock(return_value=[entry])
        self.hass.config_entries.async_update_entry = MagicMock()
        self.hass.config_entries.async_reload = AsyncMock()

        api = DomolinkKeepActiveApiView(self.hass, ota)

        # 1. GET data
        req_get = MagicMock()
        req_get.get = MagicMock(return_value=MagicMock(is_admin=True))
        res_get = asyncio.run(api.get(req_get, "data"))
        self.assertEqual(res_get["data"]["status"], "ok")
        self.assertEqual(len(res_get["data"]["rules"]), 1)

        # 2. POST toggle_ota
        req_post = MagicMock()
        req_post.get = MagicMock(return_value=MagicMock(is_admin=True))
        req_post.json = AsyncMock(return_value={"rule_id": "binary_sensor.radar", "active": True})
        res_toggle = asyncio.run(api.post(req_post, "toggle_ota"))
        self.assertEqual(res_toggle["data"]["status"], "ok")
        self.assertTrue(res_toggle["data"]["session"]["active"])

        # 3. POST update_ota_params (sliders 10-90 min, 1-60s)
        req_post.json = AsyncMock(return_value={"rule_id": "binary_sensor.radar", "duration": 50, "interval": 12})
        res_update = asyncio.run(api.post(req_post, "update_ota_params"))
        self.assertEqual(res_update["data"]["status"], "ok")
        self.assertEqual(res_update["data"]["duration"], 50)
        self.assertEqual(res_update["data"]["interval"], 12)

        # 4. POST save_rule (add second rule)
        req_post.json = AsyncMock(return_value={
            "source_entity": "switch.prise_salon",
            "name": "Prise Salon",
            "hold_duration": 10,
            "grace_period": 20,
            "ota_duration": 60,
            "ping_interval": 15,
        })
        res_save = asyncio.run(api.post(req_post, "save_rule"))
        self.assertEqual(res_save["data"]["status"], "ok")
        self.assertEqual(res_save["data"]["rules_count"], 2)

    def test_options_flow_init_menu(self):
        """Test OptionsFlow displays menu choices."""
        entry = MagicMock()
        entry.data = {CONF_SOURCE_ENTITY: "binary_sensor.radar"}
        entry.options = {}

        flow = DomoLinkKeepActiveOptionsFlowHandler(entry)
        flow.async_show_form = MagicMock(return_value={"type": "form"})

        asyncio.run(flow.async_step_init())
        flow.async_show_form.assert_called_with(
            step_id="init",
            data_schema=unittest.mock.ANY,
            description_placeholders={"count": "1"},
        )

    def test_options_flow_view_step(self):
        """Test OptionsFlow view step displays summary."""
        entry = MagicMock()
        entry.data = {
            CONF_SOURCE_ENTITY: "binary_sensor.radar_salon",
            CONF_NAME: "Radar Salon",
            CONF_HOLD_DURATION: 30,
            CONF_GRACE_PERIOD: 60,
            CONF_OPTIMISTIC: True,
            CONF_OTA_DURATION: 30,
            CONF_PING_INTERVAL: 5,
        }
        entry.options = {}

        flow = DomoLinkKeepActiveOptionsFlowHandler(entry)
        flow.async_show_form = MagicMock(return_value={"type": "form"})

        asyncio.run(flow.async_step_view())
        flow.async_show_form.assert_called_once()
        summary = flow.async_show_form.call_args[1]["description_placeholders"]["summary"]
        self.assertIn("Radar Salon", summary)
        self.assertIn("Maintien: 30s", summary)

    def test_options_flow_add_entity(self):
        """Test adding a new KeepActive entity via OptionsFlow."""
        entry = MagicMock()
        entry.data = {CONF_SOURCE_ENTITY: "binary_sensor.radar"}
        entry.options = {}

        flow = DomoLinkKeepActiveOptionsFlowHandler(entry)
        flow.async_create_entry = MagicMock(return_value={"type": "create_entry"})

        asyncio.run(flow.async_step_add({
            CONF_SOURCE_ENTITY: "switch.prise_salon",
            CONF_NAME: "Prise Salon",
            CONF_HOLD_DURATION: 10,
            CONF_GRACE_PERIOD: 20,
            CONF_OPTIMISTIC: True,
            CONF_OTA_DURATION: 40,
            CONF_PING_INTERVAL: 10,
        }))

        flow.async_create_entry.assert_called_once()
        saved_rules = flow.async_create_entry.call_args[1]["data"][CONF_RULES]
        self.assertEqual(len(saved_rules), 2)
        self.assertEqual(saved_rules[1][CONF_SOURCE_ENTITY], "switch.prise_salon")
        self.assertEqual(saved_rules[1][CONF_OTA_DURATION], 40)

    def test_options_flow_edit_entity(self):
        """Test editing an existing KeepActive entity via OptionsFlow."""
        entry = MagicMock()
        entry.data = {}
        entry.options = {
            CONF_RULES: [
                {
                    CONF_RULE_ID: "binary_sensor.motion",
                    CONF_SOURCE_ENTITY: "binary_sensor.motion",
                    CONF_NAME: "Ancien Nom",
                    CONF_HOLD_DURATION: 10,
                    CONF_GRACE_PERIOD: 10,
                    CONF_OPTIMISTIC: False,
                    CONF_OTA_DURATION: 30,
                    CONF_PING_INTERVAL: 5,
                }
            ]
        }

        flow = DomoLinkKeepActiveOptionsFlowHandler(entry)
        flow.async_create_entry = MagicMock(return_value={"type": "create_entry"})
        flow._selected_rule_id = "binary_sensor.motion"

        asyncio.run(flow.async_step_edit({
            CONF_SOURCE_ENTITY: "binary_sensor.motion",
            CONF_NAME: "Nouveau Nom",
            CONF_HOLD_DURATION: 60,
            CONF_GRACE_PERIOD: 120,
            CONF_OPTIMISTIC: True,
            CONF_OTA_DURATION: 45,
            CONF_PING_INTERVAL: 12,
        }))

        flow.async_create_entry.assert_called_once()
        saved_rules = flow.async_create_entry.call_args[1]["data"][CONF_RULES]
        self.assertEqual(saved_rules[0][CONF_NAME], "Nouveau Nom")
        self.assertEqual(saved_rules[0][CONF_HOLD_DURATION], 60)
        self.assertEqual(saved_rules[0][CONF_OTA_DURATION], 45)
        self.assertEqual(saved_rules[0][CONF_PING_INTERVAL], 12)

    def test_options_flow_delete_entity(self):
        """Test deleting a KeepActive entity via OptionsFlow with confirmation."""
        entry = MagicMock()
        entry.entry_id = "test_entry"
        entry.data = {}
        entry.options = {
            CONF_RULES: [
                {CONF_RULE_ID: "binary_sensor.motion_1", CONF_SOURCE_ENTITY: "binary_sensor.motion_1"},
                {CONF_RULE_ID: "binary_sensor.motion_2", CONF_SOURCE_ENTITY: "binary_sensor.motion_2"},
            ]
        }

        flow = DomoLinkKeepActiveOptionsFlowHandler(entry)
        flow.hass = self.hass
        flow.async_create_entry = MagicMock(return_value={"type": "create_entry"})

        asyncio.run(flow.async_step_delete({
            "rule_to_delete": "binary_sensor.motion_1",
            "confirm_delete": True,
        }))

        flow.async_create_entry.assert_called_once()
        saved_rules = flow.async_create_entry.call_args[1]["data"][CONF_RULES]
        self.assertEqual(len(saved_rules), 1)
        self.assertEqual(saved_rules[0][CONF_RULE_ID], "binary_sensor.motion_2")


if __name__ == "__main__":
    unittest.main()
