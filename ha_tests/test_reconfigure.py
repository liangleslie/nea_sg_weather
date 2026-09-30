"""Integration tests for the reconfigure flow and removal of unconfigured entities.

The reconfigure flow changes which entities an entry sets up without removing
and re-adding the integration. Whatever is switched off must be removed on
reload, and whatever stays must keep its entity ID and user customisations.
"""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import device_registry as dr, entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

import pytest

from custom_components.nea_sg_weather.const import AREAS, DOMAIN, REGIONS

from .conftest import _BASE, _ENDPOINTS, FORECAST_2HR

PREFIX = "Singapore Weather"


@pytest.fixture
def mock_nea_api_all_areas(aioclient_mock):
    """Like mock_nea_api, but the 2-hour forecast covers every area.

    The shared fixture lists three areas, which is enough for its tests; an
    "All" configuration needs a forecast for each of the 47 areas.
    """
    import copy
    import re

    forecast = copy.deepcopy(FORECAST_2HR)
    item = forecast["data"]["items"][0]
    item["forecasts"] = [{"area": area, "forecast": "Partly Cloudy"} for area in AREAS]
    forecast["data"]["area_metadata"] = [
        {"label_location": {"latitude": "1.35", "longitude": "103.82"}} for _ in AREAS
    ]
    for path, payload in _ENDPOINTS:
        aioclient_mock.get(
            re.compile(rf"{re.escape(_BASE)}/{path}"),
            json=forecast if path == "two-hr-forecast" else payload,
        )
    return aioclient_mock

ALL_ON = {
    "name": "Singapore Weather",
    "weather": True,
    "sensor": True,
    "scan_interval": 15,
    "timeout": 60,
    "sensors": {"prefix": PREFIX, "areas": ["All"], "region": True, "rain": True},
}

TWO_AREAS = {
    "name": "Singapore Weather",
    "weather": True,
    "sensor": True,
    "scan_interval": 15,
    "timeout": 60,
    "sensors": {"prefix": PREFIX, "areas": ["Ang Mo Kio", "Bedok"], "region": False, "rain": False},
}


async def _load(hass: HomeAssistant, config: dict) -> MockConfigEntry:
    entry = MockConfigEntry(domain=DOMAIN, data=config, title=config["name"])
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def _reconfigure(hass: HomeAssistant, entry: MockConfigEntry, user_input: dict):
    result = await entry.start_reconfigure_flow(hass)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reconfigure"
    result = await hass.config_entries.flow.async_configure(result["flow_id"], user_input)
    await hass.async_block_till_done()
    return result


def _unique_ids(hass: HomeAssistant, entry: MockConfigEntry, domain: str) -> set[str]:
    ent_reg = er.async_get(hass)
    return {
        e.unique_id
        for e in er.async_entries_for_config_entry(ent_reg, entry.entry_id)
        if e.domain == domain
    }


def _region_devices(hass: HomeAssistant, entry: MockConfigEntry) -> set[str]:
    wanted = {(DOMAIN, f"{entry.entry_id}_{region.lower()}") for region in REGIONS}
    dev_reg = dr.async_get(hass)
    main = dev_reg.async_get_device_by_identifier((DOMAIN, entry.entry_id), entry.entry_id)
    return {
        device.id
        for device in dr.async_entries_for_parent_device(dev_reg, main.id)
        if device.identifiers & wanted
    }


def _form(**overrides) -> dict:
    """A complete reconfigure form submission."""
    data = {
        "weather": True, "sensor": True, "areas": ["Bedok"],
        "region": False, "rain": False, "scan_interval": 15, "timeout": 60,
    }
    data.update(overrides)
    return data


async def test_form_is_prefilled_with_current_settings(hass: HomeAssistant, mock_nea_api_all_areas):
    """The reconfigure form defaults to what the entry has now."""
    entry = await _load(hass, TWO_AREAS)
    result = await entry.start_reconfigure_flow(hass)
    defaults = {
        str(key): key.default() for key in result["data_schema"].schema
        if hasattr(key, "default") and callable(key.default)
    }
    assert defaults["areas"] == ["Ang Mo Kio", "Bedok"]
    assert defaults["region"] is False
    assert defaults["rain"] is False
    assert defaults["weather"] is True
    assert defaults["scan_interval"] == 15


async def test_adding_all_areas_and_regions(hass: HomeAssistant, mock_nea_api_all_areas):
    """Switching on all areas and regions creates their sensors and devices."""
    entry = await _load(hass, TWO_AREAS)
    result = await _reconfigure(hass, entry, _form(areas=["All"], region=True))

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert entry.state is ConfigEntryState.LOADED
    assert entry.data["sensors"]["areas"] == ["All"]
    assert entry.data["sensors"]["region"] is True

    sensors = _unique_ids(hass, entry, "sensor")
    assert {f"{PREFIX} {area}" for area in AREAS} <= sensors
    assert {f"{PREFIX} {region}" for region in REGIONS} <= sensors
    assert len(_region_devices(hass, entry)) == len(REGIONS)


async def test_switched_off_entities_and_devices_are_removed(hass: HomeAssistant, mock_nea_api_all_areas):
    """Areas dropped and regions/rain switched off leave no orphans behind."""
    entry = await _load(hass, ALL_ON)
    assert _unique_ids(hass, entry, "camera")
    assert any(uid.startswith(f"{PREFIX} Rainfall ") for uid in _unique_ids(hass, entry, "sensor"))

    await _reconfigure(hass, entry, _form(areas=["Bedok"], region=False, rain=False))

    assert _unique_ids(hass, entry, "sensor") == {f"{PREFIX} Bedok", f"{PREFIX}_uv"}
    assert _unique_ids(hass, entry, "camera") == set()
    assert _unique_ids(hass, entry, "weather")  # still configured, still there
    assert _region_devices(hass, entry) == set()


async def test_weather_switched_off_is_removed(hass: HomeAssistant, mock_nea_api_all_areas):
    """Turning the weather entity off removes it from the registry."""
    entry = await _load(hass, TWO_AREAS)
    assert _unique_ids(hass, entry, "weather")
    await _reconfigure(hass, entry, _form(weather=False))
    assert _unique_ids(hass, entry, "weather") == set()
    assert hass.states.async_all("weather") == []


async def test_kept_entities_keep_ids_and_customisations(hass: HomeAssistant, mock_nea_api_all_areas):
    """Entities that stay configured keep their entity ID and user settings."""
    entry = await _load(hass, TWO_AREAS)
    ent_reg = er.async_get(hass)
    bedok = ent_reg.async_get_entity_id("sensor", DOMAIN, f"{PREFIX} Bedok")
    ent_reg.async_update_entity(bedok, hidden_by=er.RegistryEntryHider.USER)

    await _reconfigure(hass, entry, _form(areas=["All"], region=True))

    assert ent_reg.async_get_entity_id("sensor", DOMAIN, f"{PREFIX} Bedok") == bedok
    assert ent_reg.async_get(bedok).hidden_by is er.RegistryEntryHider.USER
    assert entry.data["name"] == TWO_AREAS["name"]
    assert entry.data["sensors"]["prefix"] == PREFIX


async def test_nothing_selected_is_rejected(hass: HomeAssistant, mock_nea_api_all_areas):
    """Neither weather nor sensors: the form is shown again with an error."""
    entry = await _load(hass, TWO_AREAS)
    result = await entry.start_reconfigure_flow(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], _form(weather=False, sensor=False)
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "no_entities_selected"}
    assert entry.data == TWO_AREAS


async def test_reload_without_changes_removes_nothing(hass: HomeAssistant, mock_nea_api_all_areas):
    """The cleanup only removes what is no longer configured.

    Includes the pollutant sensors, which are created disabled by default and
    so have no state: they must survive a reload.
    """
    entry = await _load(hass, ALL_ON)
    ent_reg = er.async_get(hass)
    before = {e.entity_id for e in er.async_entries_for_config_entry(ent_reg, entry.entry_id)}
    assert any(e.disabled_by for e in er.async_entries_for_config_entry(ent_reg, entry.entry_id))

    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()

    after = {e.entity_id for e in er.async_entries_for_config_entry(ent_reg, entry.entry_id)}
    assert after == before
