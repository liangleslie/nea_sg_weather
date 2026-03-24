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

## CI

GitHub Actions (`.github/workflows/tests.yml`) runs the suite on Python 3.11
and 3.12 for every push to `main`/`master` and every pull request.
