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
| `tests/test_init.py` | `get_platforms()` platform selection; which data objects `async_update` polls per configuration |
| `tests/test_sensor.py` | Sensor entity properties and formatting |
| `ha_tests/` | Boots a real HA core (`pytest-homeassistant-custom-component`) with the NEA API mocked |
| `e2e_tests/` | Live data.gov.sg API; run with `-p no:homeassistant` when the HA test plugin is installed |

Since this integration depends on Home Assistant, `tests/conftest.py` patches
`sys.modules` with lightweight stubs before any source imports happen. No full
HA installation is needed to run the tests.

The suite runs with `asyncio_mode = auto`, so write coroutine tests as
`async def` and `await` the call. Do not drive a loop by hand with
`asyncio.get_event_loop().run_until_complete(...)`: once pytest-asyncio has torn
down a loop for an earlier async test, `get_event_loop()` raises `RuntimeError`
(pytest-asyncio ≥ 1.0), so such tests pass or fail depending on file order.

## Source Layout

```
custom_components/nea_sg_weather/
├── __init__.py       # Coordinator setup, get_platforms()
├── entity.py         # Device info for the main device and region child devices
├── const.py          # All constants: areas, regions, condition maps, endpoints
├── nea.py            # Async API wrappers (Forecast2hr, Wind, Rain, …)
├── weather.py        # WeatherEntity
├── sensor.py         # Sensor entities (area, region, rain, UV, PM2.5, PSI)
├── camera.py         # Rain-map camera entities
└── config_flow.py    # Config-entry UI flow
```

## Devices and Entity Names

Entities use Home Assistant's naming model (`_attr_has_entity_name = True`),
so a friendly name is the device name followed by the entity name. Entity
names come from `translation_key`s in `strings.json` (mirrored in
`translations/en.json`); the weather entity has `_attr_name = None` and takes
the device's name.

- **Main device** — registered in `async_setup_entry` (`__init__.py`) with the
  config entry name, identifier `(DOMAIN, entry_id)`; its ID is stored on the
  coordinator as `device_id`. Weather, UV, area and rain sensors and the
  cameras attach to it via `entity.main_device_info()`.
- **Region child devices** — one per region ("Central Singapore", …), built
  by `entity.region_device_info()` with `parent_device_id` pointing at the main
  device. Region forecast, PM2.5 and PSI sensors attach to these. Child devices
  need Home Assistant 2026.9, the minimum in `manifest.json`.

Entity IDs are still set explicitly from the configured prefix, so they do not
depend on names and existing users' IDs do not change.

## Pollutant Concentration Sensors

`PSI.process_data` in `nea.py` stores the pollutant concentrations that come
with the PSI response in `PSI.concentrations`, keyed by the short names in
`const.POLLUTANT_READINGS` (`pm25_24h`, `pm10_24h`, `so2_24h`, `o3_8h`,
`co_8h`, `no2_1h`) and then by region. Missing keys give an empty dict so the
PSI sensor keeps working.

`sensor.NeaPollutantSensor` is one class for all of them, driven by the
pollutant name: translation key, device class (`POLLUTANT_DEVICE_CLASSES`) and
unit (`POLLUTANT_UNITS`, µg/m³ unless listed — NEA reports CO in mg/m³). One
entity per pollutant and region is created when region sensors are enabled,
on the region's child device, with `entity_registry_enabled_default = False`.
Entity IDs are `sensor.<prefix>_<pollutant>_<region>` (with an underscore
before the region, unlike the older region sensors) and unique IDs
`<prefix> <pollutant> <Region>`. `available` is `False` when the region is
missing from the pollutant's data.

To add a pollutant, add its reading key to `POLLUTANT_READINGS`, a device
class to `POLLUTANT_DEVICE_CLASSES`, a name to `strings.json` and
`translations/en.json`, and extend the tests in all three suites.

## Dynamic Rain Sensor Management

Rain station entities are built from the live API response (`Rain.station_list`) rather than a static list. This means the set of stations can change between coordinator updates.

`sensor.py:async_setup_entry` handles this in two stages:

**Startup cleanup** — before creating any entities, all rain sensor entries already in the entity registry for this config entry are scanned. Any whose station ID is not in the current API `station_list` are removed immediately. This catches orphans left behind by previous installs or a static station list.

**Runtime listener** — a coordinator listener registered after initial entity creation diffs `_known_rain_ids` on every update:

- **Removed stations** — looked up in the entity registry by `unique_id` and deleted via `entity_registry.async_remove()` so they do not remain as orphans in HA.
- **New stations** — instantiated as `NeaRainSensor` and registered via `async_add_entities()`.

`NeaRainSensor.available` returns `False` when the station ID is absent from `coordinator.data.rain.data`, preventing `KeyError` crashes in the brief window between a station disappearing from the API and its entity being removed.

## Reconfiguring an Entry

`config_flow.async_step_reconfigure` shows the setup choices (weather, sensor,
areas, region, rain, scan interval, timeout) prefilled from `entry.data` and
saves them with `async_update_reload_and_abort`. The entry name and sensor
prefix are never changed there: entity IDs are built from them. A weather-only
entry has no prefix yet, so it gets the entry name.

Whatever the new configuration no longer sets up is removed on setup, so the
reload after a reconfigure leaves no orphans:

- `__init__._async_remove_unconfigured` removes the entry's entities whose
  platform is not loaded any more (e.g. the weather entity, the cameras when
  rain is off, every sensor when sensors are off), and the region child
  devices when region sensors are off. Child devices are found with
  `dr.async_entries_for_parent_device` on the main device:
  `async_entries_for_config_entry` does not return them, and
  `DeviceRegistry.async_get_device` is deprecated in HA 2026.9.
- `sensor.async_setup_entry` removes the entry's sensor entities whose unique
  ID is not among the sensors it is about to add (areas dropped, regions or
  rain switched off). Disabled-by-default sensors that are still configured
  are in that list, so a reload without changes removes nothing.

`ha_tests/test_reconfigure.py` covers both, with its own API fixture whose
2-hour forecast lists all 47 areas (the shared `mock_nea_api` lists three).

## Which Data Objects Get Polled

`NeaWeatherData.async_update` in `__init__.py` only fetches the endpoints the
configured entities need. With the weather entity enabled everything is polled.
In a sensors-only configuration the set is built per option: area sensors →
2-hour forecast; region sensors → 24-hour forecast, PM2.5, PSI. The UV sensor is
created unconditionally by `sensor.async_setup_entry`, so UV is polled whenever
`get_platforms()` includes the sensor platform; rain sensors live in the same
platform, so rainfall is polled when the rain option is on *and* the sensor
platform loads (the rain cameras read no coordinator data).

When adding an entity that reads a new data object, add that object to every
branch whose configuration creates the entity, and extend
`tests/test_init.py::TestAsyncUpdatePolledObjects`. Entities that read an
unpolled object silently show the object's constructor defaults (e.g. UV = 0).

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

GitHub Actions (`.github/workflows/tests.yml`) runs the suite on Python 3.14,
the version current Home Assistant requires, for every push to `main`/`master`
and every pull request.

The HA integration test workflow (`.github/workflows/ha-test.yml`) uses
`requirements-ha-test.txt`, which pins `pytest-homeassistant-custom-component`
to an exact version (and with it the Home Assistant release the tests boot).
Bump the pin to test against a newer HA. It also installs `PyTurboJPEG`
(HA's camera component imports it), so tests can load the rain-map cameras. The `ha_tests/` fixtures mock the NEA
API with HA's `aioclient_mock`, which patches the shared session returned by
`async_get_clientsession()`.
