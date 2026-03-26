"""End-to-end tests: hit the real NEA / data.gov.sg API and validate responses.

These tests require network access and are intentionally kept separate from the
unit tests in tests/ (which mock aiohttp).  They are skipped automatically when
the network is unavailable or the API is unreachable.

Run locally:
    pytest e2e_tests/ -v

In CI they are triggered by the separate e2e.yml workflow.
"""
from __future__ import annotations

import pytest
import aiohttp

from custom_components.nea_sg_weather.nea import (
    Forecast2hr,
    Forecast24hr,
    Forecast4day,
    Temperature,
    Humidity,
    Wind,
    Rain,
    UVIndex,
    PM25,
)

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _fetch(obj):
    """Run async_init on a NeaData (or Wind) object and return it."""
    try:
        async with aiohttp.ClientSession() as session:
            await obj.async_init(session)
    except aiohttp.ClientConnectorError as exc:
        pytest.skip(f"Network unavailable: {exc}")
    except aiohttp.ClientResponseError as exc:
        pytest.skip(f"API returned error: {exc}")
    return obj


# ---------------------------------------------------------------------------
# 2-hour forecast
# ---------------------------------------------------------------------------

async def test_forecast_2hr_returns_area_data():
    f = await _fetch(Forecast2hr())

    assert f.timestamp, "timestamp should be populated"
    assert f.current_condition, "current_condition should be non-empty"
    assert isinstance(f.area_forecast, dict), "area_forecast should be a dict"
    assert len(f.area_forecast) > 0, "area_forecast should contain at least one area"

    # Each area entry must have a 'forecast' key with a non-empty string
    for area, data in f.area_forecast.items():
        assert isinstance(area, str), f"area key {area!r} should be a string"
        assert "forecast" in data, f"area {area!r} missing 'forecast' key"
        assert data["forecast"], f"area {area!r} has empty forecast"


# ---------------------------------------------------------------------------
# 24-hour forecast
# ---------------------------------------------------------------------------

async def test_forecast_24hr_returns_region_data():
    f = await _fetch(Forecast24hr())

    assert f.timestamp, "timestamp should be populated"
    assert isinstance(f.region_forecast, dict), "region_forecast should be a dict"
    assert len(f.region_forecast) > 0, "region_forecast should contain at least one region"

    expected_regions = {"west", "east", "central", "south", "north"}
    for region in f.region_forecast:
        assert region in expected_regions, f"Unexpected region: {region!r}"
        periods = f.region_forecast[region]
        assert isinstance(periods, list) and len(periods) > 0, (
            f"region {region!r} should have at least one forecast period"
        )


# ---------------------------------------------------------------------------
# 4-day forecast
# ---------------------------------------------------------------------------

async def test_forecast_4day_returns_daily_entries():
    f = await _fetch(Forecast4day())

    assert isinstance(f.forecast, list), "forecast should be a list"
    assert len(f.forecast) > 0, "forecast should have at least one entry"

    required_keys = {
        "condition", "native_temperature", "native_templow",
        "native_wind_speed", "wind_bearing", "datetime",
    }
    for i, entry in enumerate(f.forecast):
        missing = required_keys - entry.keys()
        assert not missing, f"forecast[{i}] missing keys: {missing}"


# ---------------------------------------------------------------------------
# Temperature
# ---------------------------------------------------------------------------

async def test_temperature_returns_plausible_value():
    t = await _fetch(Temperature())

    assert t.timestamp, "timestamp should be populated"
    # Singapore temperatures are roughly 20–40 °C
    assert 15 <= t.temp_avg <= 45, (
        f"temp_avg {t.temp_avg} outside plausible range for Singapore"
    )


# ---------------------------------------------------------------------------
# Humidity
# ---------------------------------------------------------------------------

async def test_humidity_returns_plausible_value():
    h = await _fetch(Humidity())

    assert h.timestamp, "timestamp should be populated"
    # Relative humidity 0–100 %
    assert 0 <= h.humd_avg <= 100, (
        f"humd_avg {h.humd_avg} is outside 0-100 range"
    )


# ---------------------------------------------------------------------------
# Wind
# ---------------------------------------------------------------------------

async def test_wind_returns_speed_and_bearing():
    w = await _fetch(Wind())

    assert w.wind_speed_avg >= 0, "wind_speed_avg should be non-negative"
    assert 0 <= w.wind_dir_avg <= 360, (
        f"wind_dir_avg {w.wind_dir_avg} outside 0-360 range"
    )


# ---------------------------------------------------------------------------
# Rain
# ---------------------------------------------------------------------------

async def test_rain_returns_station_data():
    r = await _fetch(Rain())

    assert isinstance(r.station_list, list) and len(r.station_list) > 0, (
        "station_list should be a non-empty list"
    )
    assert isinstance(r.data, dict) and len(r.data) > 0, (
        "data should be a non-empty dict"
    )

    for station_id, reading in r.data.items():
        assert "value" in reading, f"station {station_id!r} missing 'value'"
        assert "name" in reading, f"station {station_id!r} missing 'name'"
        assert reading["value"] >= 0, (
            f"station {station_id!r} has negative rainfall value"
        )


# ---------------------------------------------------------------------------
# UV Index
# ---------------------------------------------------------------------------

async def test_uv_index_returns_plausible_value():
    u = await _fetch(UVIndex())

    # UV index scale: 0–20 (Singapore can hit 15+)
    assert 0 <= u.uv_index <= 20, (
        f"uv_index {u.uv_index} outside expected range"
    )


# ---------------------------------------------------------------------------
# PM2.5
# ---------------------------------------------------------------------------

async def test_pm25_returns_regional_data():
    p = await _fetch(PM25())

    assert p.timestamp, "timestamp should be populated"
    assert isinstance(p.data, dict) and len(p.data) > 0, (
        "PM2.5 data should be a non-empty dict"
    )

    expected_regions = {"west", "east", "central", "south", "north"}
    for region in p.data:
        assert region in expected_regions, f"Unexpected PM2.5 region: {region!r}"
        assert p.data[region] >= 0, f"PM2.5 value for {region!r} is negative"
