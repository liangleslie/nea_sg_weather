"""Fixtures for Home Assistant integration tests."""
import re
import threading
import pytest
from aioresponses import aioresponses as AioResponses


# pytest-homeassistant-custom-component blocks custom integrations by default.
# This autouse fixture opts every test in ha_tests/ into the allow-list so HA
# can find and load the integration from the local custom_components/ directory.
@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Allow HA to load integrations from the local custom_components/ directory."""
    yield


@pytest.fixture(autouse=True)
def verify_cleanup():
    """Override PHAC's verify_cleanup to also allow aiohttp's daemon thread.

    aiohttp ≥3.9 spawns a '_run_safe_shutdown_loop' thread when the connector
    is first used (via HA's shared ClientSession). PHAC only whitelists
    _DummyThread and 'waitpid-' threads, so we extend that check here.
    """
    threads_before = {t for t in threading.enumerate() if t.is_alive()}
    yield
    threads_after = {t for t in threading.enumerate() if t.is_alive()}
    for thread in threads_after - threads_before:
        assert (
            isinstance(thread, threading._DummyThread)
            or thread.name.startswith("waitpid-")
            or "_run_safe_shutdown_loop" in thread.name
            or thread.name.startswith("SyncWorker_")
        ), f"Unexpected thread left after test: {thread.name!r}"


# ---------------------------------------------------------------------------
# Canned API responses — realistic enough that nea.py process_data() runs
# (each payload stringifies to well over 120 characters).
# ---------------------------------------------------------------------------

FORECAST_2HR = {
    "data": {
        "items": [{
            "timestamp": "2024-01-01T12:00:00+08:00",
            "forecasts": [
                {"area": "Ang Mo Kio", "forecast": "Partly Cloudy"},
                {"area": "Bedok", "forecast": "Partly Cloudy"},
                {"area": "Bishan", "forecast": "Sunny"},
            ],
        }],
        "area_metadata": [
            {"label_location": {"latitude": "1.3691", "longitude": "103.8454"}},
            {"label_location": {"latitude": "1.3236", "longitude": "103.9273"}},
            {"label_location": {"latitude": "1.3526", "longitude": "103.8352"}},
        ],
    },
}

FORECAST_24HR = {
    "data": {
        "records": [{
            "timestamp": "2024-01-01T12:00:00+08:00",
            "periods": [{
                "timePeriod": {"start": "2024-01-01T06:00:00+08:00"},
                "regions": {
                    "west":    {"text": "Partly Cloudy"},
                    "east":    {"text": "Sunny"},
                    "central": {"text": "Cloudy"},
                    "south":   {"text": "Partly Cloudy"},
                    "north":   {"text": "Sunny"},
                },
            }],
        }],
    },
}

FORECAST_4DAY = {
    "data": {
        "records": [{
            "forecasts": [{
                "timestamp": "2024-01-02T00:00:00+08:00",
                "forecast": {"text": "Partly Cloudy"},
                "temperature": {"high": 34, "low": 25},
                "wind": {"speed": {"high": 20, "low": 10}, "direction": "NE"},
            }],
        }],
    },
}

TEMPERATURE = {
    "data": {
        "readings": [{
            "timestamp": "2024-01-01T12:00:00+08:00",
            "data": [
                {"stationId": "S01", "value": 28.5},
                {"stationId": "S02", "value": 30.0},
            ],
        }],
    },
}

HUMIDITY = {
    "data": {
        "readings": [{
            "timestamp": "2024-01-01T12:00:00+08:00",
            "data": [
                {"stationId": "S01", "value": 75.0},
                {"stationId": "S02", "value": 80.0},
            ],
        }],
    },
}

WIND_DIRECTION = {
    "data": {
        "readings": [{
            "timestamp": "2024-01-01T12:00:00+08:00",
            "data": [
                {"stationId": "S01", "value": 45},
                {"stationId": "S02", "value": 90},
            ],
        }],
    },
}

WIND_SPEED = {
    "data": {
        "readings": [{
            "timestamp": "2024-01-01T12:00:00+08:00",
            "data": [
                {"stationId": "S01", "value": 10},
                {"stationId": "S02", "value": 15},
            ],
        }],
    },
}

RAINFALL = {
    "data": {
        "readings": [{
            "timestamp": "2024-01-01T12:00:00+08:00",
            "data": [{"stationId": "S117", "value": 0.0}],
        }],
        "stations": [{
            "id": "S117",
            "name": "Banyan Road",
            "location": {"latitude": 1.256, "longitude": 103.679},
        }],
    },
}

UV_INDEX = {
    "data": {
        "records": [{
            "timestamp": "2024-01-01T12:00:00+08:00",
            "index": [{"value": 5}],
        }],
    },
}

PM25 = {
    "data": {
        "items": [{
            "timestamp": "2024-01-01T12:00:00+08:00",
            "readings": {
                "pm25_one_hourly": {
                    "west": 15, "east": 18, "central": 20, "south": 16, "north": 14,
                },
            },
        }],
    },
}

_BASE = "https://api-open.data.gov.sg/v2/real-time/api"

_ENDPOINTS = [
    ("two-hr-forecast",        FORECAST_2HR),
    ("twenty-four-hr-forecast", FORECAST_24HR),
    ("four-day-outlook",       FORECAST_4DAY),
    ("air-temperature",        TEMPERATURE),
    ("relative-humidity",      HUMIDITY),
    ("wind-direction",         WIND_DIRECTION),
    ("wind-speed",             WIND_SPEED),
    ("rainfall",               RAINFALL),
    ("uv",                     UV_INDEX),
    ("pm25",                   PM25),
]


@pytest.fixture
def mock_nea_api():
    """Intercept all NEA API calls and return canned responses.

    Uses regex matching so query-string parameters (date_time=…) are ignored.
    repeat=True allows the coordinator to call each endpoint more than once.
    """
    with AioResponses() as m:
        for path, payload in _ENDPOINTS:
            m.get(
                re.compile(rf"{re.escape(_BASE)}/{path}"),
                payload=payload,
                repeat=True,
            )
        yield m
