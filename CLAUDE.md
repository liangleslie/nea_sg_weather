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

## CI

GitHub Actions (`.github/workflows/tests.yml`) runs the suite on Python 3.11
and 3.12 for every push to `main`/`master` and every pull request.
