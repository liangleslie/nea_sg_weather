"""Integration tests: boot nea_sg_weather inside a real Home Assistant instance.

These tests use pytest-homeassistant-custom-component which spins up a
lightweight but real HA core.  All NEA API HTTP calls are intercepted by the
mock_nea_api fixture (aioresponses), so no network access is required.

Run with:
    pytest ha_tests/ -v
"""
from __future__ import annotations

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.nea_sg_weather.const import DOMAIN

# ---------------------------------------------------------------------------
# Config entry data fixtures
# ---------------------------------------------------------------------------

WEATHER_ONLY = {
    "name": "Singapore Weather",
    "weather": True,
    "sensor": False,
    "scan_interval": 15,
    "timeout": 60,
}

WITH_AREA_SENSORS = {
    "name": "Singapore Weather",
    "weather": True,
    "sensor": True,
    "scan_interval": 15,
    "timeout": 60,
    "sensors": {
        "prefix": "Singapore Weather",
        "areas": ["Ang Mo Kio", "Bedok"],
        "region": False,
        "rain": False,
    },
}

WITH_REGION_SENSORS = {
    "name": "Singapore Weather",
    "weather": False,
    "sensor": True,
    "scan_interval": 15,
    "timeout": 60,
    "sensors": {
        "prefix": "Singapore Weather",
        "areas": ["None"],
        "region": True,
        "rain": False,
    },
}


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

async def _load(hass: HomeAssistant, config: dict) -> MockConfigEntry:
    """Create, register, and set up a config entry; return it."""
    entry = MockConfigEntry(domain=DOMAIN, data=config, title=config["name"])
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


# ---------------------------------------------------------------------------
# Entry lifecycle
# ---------------------------------------------------------------------------

async def test_entry_loads_successfully(hass: HomeAssistant, mock_nea_api):
    """Config entry reaches LOADED state."""
    entry = await _load(hass, WEATHER_ONLY)
    assert entry.state == ConfigEntryState.LOADED


async def test_coordinator_stored_in_hass_data(hass: HomeAssistant, mock_nea_api):
    """Coordinator is accessible via hass.data after setup."""
    entry = await _load(hass, WEATHER_ONLY)
    assert DOMAIN in hass.data
    assert entry.entry_id in hass.data[DOMAIN]


async def test_entry_unloads_successfully(hass: HomeAssistant, mock_nea_api):
    """Config entry transitions to NOT_LOADED after unload."""
    entry = await _load(hass, WEATHER_ONLY)
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state == ConfigEntryState.NOT_LOADED


async def test_unload_removes_coordinator_from_hass_data(hass: HomeAssistant, mock_nea_api):
    """Coordinator is removed from hass.data after unload."""
    entry = await _load(hass, WEATHER_ONLY)
    await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.entry_id not in hass.data.get(DOMAIN, {})


# ---------------------------------------------------------------------------
# Weather entity
# ---------------------------------------------------------------------------

async def test_weather_entity_registered(hass: HomeAssistant, mock_nea_api):
    """A weather entity appears in the state machine after setup."""
    await _load(hass, WEATHER_ONLY)
    states = hass.states.async_all("weather")
    assert len(states) == 1
    assert states[0].name == "Singapore Weather"


async def test_weather_entity_has_temperature_attribute(hass: HomeAssistant, mock_nea_api):
    """Weather entity exposes a numeric temperature."""
    await _load(hass, WEATHER_ONLY)
    state = hass.states.get("weather.singapore_weather")
    assert state is not None
    temp = state.attributes.get("temperature")
    assert isinstance(temp, (int, float))


async def test_weather_entity_condition_is_valid(hass: HomeAssistant, mock_nea_api):
    """Weather entity condition is a recognised HA weather state string."""
    await _load(hass, WEATHER_ONLY)
    state = hass.states.get("weather.singapore_weather")
    assert state is not None
    assert state.state not in ("unavailable", "unknown")


async def test_weather_entity_humidity_attribute(hass: HomeAssistant, mock_nea_api):
    """Weather entity exposes humidity."""
    await _load(hass, WEATHER_ONLY)
    state = hass.states.get("weather.singapore_weather")
    humidity = state.attributes.get("humidity")
    assert isinstance(humidity, (int, float))


# ---------------------------------------------------------------------------
# Sensor entities
# ---------------------------------------------------------------------------

async def test_area_sensor_entities_registered(hass: HomeAssistant, mock_nea_api):
    """Area sensor entities appear in the state machine."""
    await _load(hass, WITH_AREA_SENSORS)
    names = {s.name for s in hass.states.async_all("sensor")}
    assert any("Ang Mo Kio" in name for name in names)
    assert any("Bedok" in name for name in names)


async def test_region_sensor_entities_registered(hass: HomeAssistant, mock_nea_api):
    """Region sensor entities (West/East/Central/South/North) appear in the state machine."""
    await _load(hass, WITH_REGION_SENSORS)
    names = {s.name for s in hass.states.async_all("sensor")}
    regions = ("West", "East", "Central", "South", "North")
    assert any(region in name for name in names for region in regions)
