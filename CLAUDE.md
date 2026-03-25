# NEA Singapore Weather — Developer Guide

## Project Overview

Home Assistant custom integration providing real-time weather data for Singapore via the NEA / data.gov.sg API.

## Running the Test Suite

Install test dependencies:

```bash
pip install -r requirements-test.txt
```

Run all tests:

```bash
pytest
```

Run with verbose output:

```bash
pytest -v
```

Run a specific test file:

```bash
pytest tests/test_nea.py -v
```

Run with coverage:

```bash
pip install pytest-cov
pytest --cov=custom_components/nea_sg_weather --cov-report=term-missing
```

## Test Architecture

Tests live in `tests/` and are structured by source module:

| File | Tests for |
|---|---|
| `tests/conftest.py` | Home Assistant module stubs (applied globally) |
| `tests/test_const.py` | Constants, mappings, area/region lists, endpoints |
| `tests/test_nea.py` | API wrapper data-processing logic (`nea.py`) |
| `tests/test_init.py` | `get_platforms()` platform selection logic |
| `tests/test_sensor.py` | Sensor entity properties and formatting |

Since this integration depends on Home Assistant, `tests/conftest.py` patches
`sys.modules` with lightweight stubs before any source imports happen. No full
HA installation is needed to run the tests.

## Source Layout

```
custom_components/nea_sg_weather/
├── __init__.py       # Coordinator setup, get_platforms()
├── const.py          # All constants: areas, regions, condition maps, endpoints
├── nea.py            # Async API wrappers (Forecast2hr, Wind, Rain, …)
├── weather.py        # WeatherEntity
├── sensor.py         # Sensor entities (area, region, rain, UV, PM2.5)
├── camera.py         # Rain-map camera entities
└── config_flow.py    # Config-entry UI flow
```

## Dynamic Rain Sensor Management

Rain station entities are built from the live API response (`Rain.station_list`) rather than a static list. This means the set of stations can change between coordinator updates.

`sensor.py:async_setup_entry` handles this in two stages:

**Startup cleanup** — before creating any entities, all rain sensor entries already in the entity registry for this config entry are scanned. Any whose station ID is not in the current API `station_list` are removed immediately. This catches orphans left behind by previous installs or a static station list.

**Runtime listener** — a coordinator listener registered after initial entity creation diffs `_known_rain_ids` on every update:

- **Removed stations** — looked up in the entity registry by `unique_id` and deleted via `entity_registry.async_remove()` so they do not remain as orphans in HA.
- **New stations** — instantiated as `NeaRainSensor` and registered via `async_add_entities()`.

`NeaRainSensor.available` returns `False` when the station ID is absent from `coordinator.data.rain.data`, preventing `KeyError` crashes in the brief window between a station disappearing from the API and its entity being removed.

## API Failure Handling

Each API call in `nea.py` is wrapped with a 10-second per-request timeout (`_REQUEST_TIMEOUT`). `NeaData.fetch_data` handles failures in two stages:

1. **Primary endpoint** — if the request raises `aiohttp.ClientError` or `asyncio.TimeoutError`, or the response is too short, the secondary endpoint is tried (where configured).
2. **Secondary endpoint** — if this also fails, the exception propagates to the caller.

`Wind.calc_wind_status` returns zero wind (rather than crashing with `ZeroDivisionError`) when no matching station pairs are found.

### Stale data preservation

`NeaWeatherData` keeps a `_last_data` reference to the most recent successful fetch. Inside `async_update`, every data object is fetched inside its own `try/except`. On failure:

- If `_last_data` exists, `setattr(self.data, attr, getattr(self._last_data, attr))` substitutes the stale object so entities keep their last known value.
- If there is no previous data (first run, all objects failed), `UpdateFailed` is raised as normal.

The class-name → attribute mapping is kept in `_ATTR_BY_CLASS` at module level in `__init__.py`.

## CI

GitHub Actions (`.github/workflows/tests.yml`) runs the suite on Python 3.11
and 3.12 for every push to `main`/`master` and every pull request.

The HA integration test workflow (`.github/workflows/ha-test.yml`) uses
`requirements-ha-test.txt`. The `pytest-homeassistant-custom-component` package
is pinned to `>=0.13.0,<1.0.0` because version 1.x does not exist for Python 3.12.
