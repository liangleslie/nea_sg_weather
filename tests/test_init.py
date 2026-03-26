"""Tests for custom_components/nea_sg_weather/__init__.py"""
import pytest
from unittest.mock import MagicMock

from custom_components.nea_sg_weather import get_platforms


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_config_entry(
    weather=True,
    sensor=False,
    areas=None,
    region=False,
    rain=False,
):
    """Build a minimal mock ConfigEntry."""
    config_entry = MagicMock()
    config_entry.data = {
        "weather": weather,
        "sensor": sensor,
        "sensors": {
            "areas": areas if areas is not None else ["None"],
            "region": region,
            "rain": rain,
            "prefix": "nea",
        },
    }
    return config_entry


# ---------------------------------------------------------------------------
# get_platforms
# ---------------------------------------------------------------------------

class TestGetPlatforms:
    def test_weather_only_adds_weather_platform(self):
        result = get_platforms(_make_config_entry(weather=True, sensor=False))
        assert "weather" in result["platforms"]

    def test_weather_only_no_sensor_platform(self):
        result = get_platforms(_make_config_entry(weather=True, sensor=False))
        assert "sensor" not in result["platforms"]
        assert "camera" not in result["platforms"]

    def test_no_entities_empty_platforms(self):
        result = get_platforms(_make_config_entry(weather=False, sensor=False))
        assert len(result["platforms"]) == 0
        assert len(result["entities"]) == 0

    def test_sensor_areas_adds_sensor_platform(self):
        result = get_platforms(_make_config_entry(
            weather=False, sensor=True, areas=["Ang Mo Kio"]
        ))
        assert "sensor" in result["platforms"]

    def test_sensor_areas_none_no_sensor(self):
        result = get_platforms(_make_config_entry(
            weather=False, sensor=True, areas=["None"]
        ))
        assert "sensor" not in result["platforms"]

    def test_sensor_region_adds_sensor_platform(self):
        result = get_platforms(_make_config_entry(
            weather=False, sensor=True, areas=["None"], region=True
        ))
        assert "sensor" in result["platforms"]

    def test_rain_adds_camera_platform(self):
        result = get_platforms(_make_config_entry(
            weather=False, sensor=True, areas=["None"], rain=True
        ))
        assert "camera" in result["platforms"]

    def test_all_enabled_all_platforms(self):
        result = get_platforms(_make_config_entry(
            weather=True, sensor=True, areas=["All"], region=True, rain=True
        ))
        for platform in ["weather", "sensor", "camera"]:
            assert platform in result["platforms"]

    def test_platforms_is_list(self):
        result = get_platforms(_make_config_entry(weather=True))
        assert isinstance(result["platforms"], list)

    def test_entities_contains_weather_key(self):
        result = get_platforms(_make_config_entry(weather=True, sensor=False))
        assert "weather" in result["entities"]

    def test_entities_contains_areas_key(self):
        result = get_platforms(_make_config_entry(
            weather=False, sensor=True, areas=["Bedok"]
        ))
        assert "areas" in result["entities"]

    def test_entities_contains_region_key(self):
        result = get_platforms(_make_config_entry(
            weather=False, sensor=True, areas=["None"], region=True
        ))
        assert "region" in result["entities"]

    def test_entities_contains_rain_key(self):
        result = get_platforms(_make_config_entry(
            weather=False, sensor=True, areas=["None"], rain=True
        ))
        assert "rain" in result["entities"]

    def test_no_duplicate_platforms(self):
        result = get_platforms(_make_config_entry(
            weather=True, sensor=True, areas=["Ang Mo Kio"], region=True, rain=True
        ))
        assert len(result["platforms"]) == len(set(result["platforms"]))

    def test_weather_and_sensor_areas(self):
        result = get_platforms(_make_config_entry(
            weather=True, sensor=True, areas=["Ang Mo Kio"]
        ))
        assert "weather" in result["platforms"]
        assert "sensor" in result["platforms"]

    def test_all_areas_keyword_adds_sensor(self):
        result = get_platforms(_make_config_entry(
            weather=False, sensor=True, areas=["All"]
        ))
        assert "sensor" in result["platforms"]
