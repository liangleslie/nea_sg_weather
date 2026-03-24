"""Tests for custom_components/nea_sg_weather/sensor.py entity classes."""
import pytest
from unittest.mock import MagicMock

from custom_components.nea_sg_weather.sensor import (
    NeaAreaSensor,
    NeaRegionSensor,
    NeaRainSensor,
    NeaUVSensor,
    NeaPM25Sensor,
)
from custom_components.nea_sg_weather.const import FORECAST_ICON_BASE_URL


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

def _make_coordinator(
    area="Ang Mo Kio",
    area_forecast_value="Partly Cloudy",
    area_timestamp="2024-01-01T12:00:00+08:00",
    region="west",
    region_forecast=None,
    region_timestamp="2024-01-01T12:00:00+08:00",
    rain_station="S77",
    rain_value=1.2,
    rain_name="Alexandra Road",
    rain_timestamp="2024-01-01T12:00:00+08:00",
    uv_index=5,
    pm25_data=None,
):
    coord = MagicMock()
    coord.data.forecast2hr.area_forecast = {
        area: {
            "forecast": area_forecast_value,
            "location": {"latitude": 1.375, "longitude": 103.839},
        }
    }
    coord.data.forecast2hr.timestamp = area_timestamp
    coord.data.forecast24hr.region_forecast = {
        region: [
            ["Today morning", "Partly Cloudy"],
            ["Today afternoon", "Sunny"],
            ["Today evening", "Cloudy"],
        ]
    }
    coord.data.forecast24hr.timestamp = region_timestamp
    coord.data.rain.data = {
        rain_station: {
            "value": rain_value,
            "name": rain_name,
            "location": {"latitude": 1.2937, "longitude": 103.8125},
        }
    }
    coord.data.rain.timestamp = rain_timestamp
    coord.data.uvindex.uv_index = uv_index
    coord.data.pm25.data = pm25_data or {"west": 12, "east": 10, "central": 8, "south": 9, "north": 11}
    return coord


def _make_config(prefix="nea"):
    return {
        "sensors": {
            "prefix": prefix,
            "areas": ["All"],
            "region": True,
            "rain": False,
        }
    }


# ---------------------------------------------------------------------------
# NeaAreaSensor
# ---------------------------------------------------------------------------

class TestNeaAreaSensor:
    def test_unique_id(self):
        coord = _make_coordinator()
        sensor = NeaAreaSensor(coord, _make_config("nea"), "Ang Mo Kio", "entry1")
        assert sensor.unique_id == "nea Ang Mo Kio"

    def test_name(self):
        coord = _make_coordinator()
        sensor = NeaAreaSensor(coord, _make_config(), "Bedok", "entry1")
        assert sensor.name == "Bedok"

    def test_entity_id_lowercase_underscored(self):
        coord = _make_coordinator(area="Ang Mo Kio")
        sensor = NeaAreaSensor(coord, _make_config("nea"), "Ang Mo Kio", "entry1")
        assert sensor.entity_id == "sensor.nea_ang_mo_kio"

    def test_entity_id_prefix_reflected(self):
        coord = _make_coordinator(area="Bedok")
        sensor = NeaAreaSensor(coord, _make_config("myprefix"), "Bedok", "entry1")
        assert "myprefix" in sensor.entity_id

    def test_state_returns_forecast(self):
        coord = _make_coordinator(area_forecast_value="Thundery Showers")
        sensor = NeaAreaSensor(coord, _make_config(), "Ang Mo Kio", "entry1")
        assert sensor.state == "Thundery Showers"

    def test_entity_picture_uses_icon_code(self):
        coord = _make_coordinator(area_forecast_value="Sunny")
        sensor = NeaAreaSensor(coord, _make_config(), "Ang Mo Kio", "entry1")
        # "Sunny" maps to icon code "SU"
        assert sensor.entity_picture == FORECAST_ICON_BASE_URL + "SU.png"

    def test_entity_picture_unknown_condition_uses_na(self):
        coord = _make_coordinator(area_forecast_value="Unknown Condition XYZ")
        sensor = NeaAreaSensor(coord, _make_config(), "Ang Mo Kio", "entry1")
        assert sensor.entity_picture == FORECAST_ICON_BASE_URL + "NA.png"

    def test_extra_state_attributes_timestamp(self):
        coord = _make_coordinator(area_timestamp="2024-03-15T08:00:00+08:00")
        sensor = NeaAreaSensor(coord, _make_config(), "Ang Mo Kio", "entry1")
        attrs = sensor.extra_state_attributes
        assert attrs["Updated at"] == "2024-03-15T08:00:00+08:00"

    def test_extra_state_attributes_location(self):
        coord = _make_coordinator()
        sensor = NeaAreaSensor(coord, _make_config(), "Ang Mo Kio", "entry1")
        attrs = sensor.extra_state_attributes
        assert "latitude" in attrs
        assert "longitude" in attrs
        assert attrs["latitude"] == pytest.approx(1.375)
        assert attrs["longitude"] == pytest.approx(103.839)

    def test_device_info_returns_dict_like(self):
        coord = _make_coordinator()
        sensor = NeaAreaSensor(coord, _make_config(), "Ang Mo Kio", "entry1")
        info = sensor.device_info
        assert info is not None


# ---------------------------------------------------------------------------
# NeaRegionSensor
# ---------------------------------------------------------------------------

class TestNeaRegionSensor:
    def _make_coord(self, region):
        coord = _make_coordinator(region=region.lower())
        return coord

    def test_unique_id(self):
        coord = self._make_coord("West")
        sensor = NeaRegionSensor(coord, _make_config("nea"), "West", "entry1")
        assert sensor.unique_id == "nea West"

    def test_name_non_central(self):
        coord = self._make_coord("West")
        sensor = NeaRegionSensor(coord, _make_config(), "West", "entry1")
        assert sensor.name == "Weather in Western Singapore"

    def test_name_central(self):
        coord = self._make_coord("Central")
        coord.data.forecast24hr.region_forecast["central"] = [
            ["Today morning", "Cloudy"]
        ]
        sensor = NeaRegionSensor(coord, _make_config(), "Central", "entry1")
        assert sensor.name == "Weather in Central Singapore"

    def test_name_east(self):
        coord = self._make_coord("East")
        coord.data.forecast24hr.region_forecast["east"] = [
            ["Today morning", "Sunny"]
        ]
        sensor = NeaRegionSensor(coord, _make_config(), "East", "entry1")
        assert sensor.name == "Weather in Eastern Singapore"

    def test_entity_id(self):
        coord = self._make_coord("North")
        coord.data.forecast24hr.region_forecast["north"] = [
            ["Today morning", "Fair"]
        ]
        sensor = NeaRegionSensor(coord, _make_config("nea"), "North", "entry1")
        assert sensor.entity_id == "sensor.nea_north"

    def test_state_first_period(self):
        coord = self._make_coord("West")
        sensor = NeaRegionSensor(coord, _make_config(), "West", "entry1")
        assert sensor.state == "Partly Cloudy"

    def test_extra_state_attributes_includes_periods(self):
        coord = self._make_coord("West")
        sensor = NeaRegionSensor(coord, _make_config(), "West", "entry1")
        attrs = sensor.extra_state_attributes
        assert "Today morning" in attrs
        assert "Updated at" in attrs

    def test_extra_state_attributes_timestamp(self):
        coord = _make_coordinator(region="west", region_timestamp="2024-06-01T06:00:00+08:00")
        sensor = NeaRegionSensor(coord, _make_config(), "West", "entry1")
        assert sensor.extra_state_attributes["Updated at"] == "2024-06-01T06:00:00+08:00"


# ---------------------------------------------------------------------------
# NeaRainSensor
# ---------------------------------------------------------------------------

class TestNeaRainSensor:
    def test_unique_id(self):
        coord = _make_coordinator(rain_station="S77")
        sensor = NeaRainSensor(coord, _make_config("nea"), "S77", "entry1")
        assert sensor.unique_id == "nea Rainfall S77"

    def test_name(self):
        coord = _make_coordinator(rain_station="S77")
        sensor = NeaRainSensor(coord, _make_config(), "S77", "entry1")
        assert sensor.name == "S77"

    def test_entity_id(self):
        coord = _make_coordinator(rain_station="S77")
        sensor = NeaRainSensor(coord, _make_config("nea"), "S77", "entry1")
        assert sensor.entity_id == "sensor.nea_rainfall_s77"

    def test_native_value(self):
        coord = _make_coordinator(rain_station="S77", rain_value=2.5)
        sensor = NeaRainSensor(coord, _make_config(), "S77", "entry1")
        assert sensor.native_value == 2.5

    def test_icon(self):
        coord = _make_coordinator()
        sensor = NeaRainSensor(coord, _make_config(), "S77", "entry1")
        assert sensor.icon == "mdi:weather-pouring"

    @pytest.mark.parametrize("value,expected_qty", [
        (0, "0"),
        (0.1, "0.2"),
        (0.34, "0.2"),
        (0.35, "0.5"),
        (0.74, "0.5"),
        (0.75, "1"),
        (1.49, "1"),
        (1.5, "2"),
        (2.49, "2"),
        (2.5, "3"),
        (3.49, "3"),
        (3.5, "4"),
        (4.49, "4"),
        (4.5, "5"),
        (10.0, "5"),
    ])
    def test_entity_picture_thresholds(self, value, expected_qty):
        coord = _make_coordinator(rain_station="S77", rain_value=value)
        sensor = NeaRainSensor(coord, _make_config(), "S77", "entry1")
        assert sensor.entity_picture == f"/local/weather/{expected_qty}.png"

    def test_extra_state_attributes_location(self):
        coord = _make_coordinator(rain_station="S77")
        sensor = NeaRainSensor(coord, _make_config(), "S77", "entry1")
        attrs = sensor.extra_state_attributes
        assert "latitude" in attrs
        assert "longitude" in attrs
        assert "Location name" in attrs
        assert attrs["Location name"] == "Alexandra Road"

    def test_extra_state_attributes_timestamp(self):
        coord = _make_coordinator(rain_station="S77", rain_timestamp="2024-03-01T08:00:00+08:00")
        sensor = NeaRainSensor(coord, _make_config(), "S77", "entry1")
        assert sensor.extra_state_attributes["Updated at"] == "2024-03-01T08:00:00+08:00"


# ---------------------------------------------------------------------------
# NeaUVSensor
# ---------------------------------------------------------------------------

class TestNeaUVSensor:
    def test_unique_id(self):
        coord = _make_coordinator()
        sensor = NeaUVSensor(coord, _make_config("nea"), "entry1")
        assert sensor.unique_id == "nea_uv"

    def test_name(self):
        coord = _make_coordinator()
        sensor = NeaUVSensor(coord, _make_config(), "entry1")
        assert sensor.name == "UV Index in Singapore"

    def test_entity_id(self):
        coord = _make_coordinator()
        sensor = NeaUVSensor(coord, _make_config("nea"), "entry1")
        assert sensor.entity_id == "sensor.nea_uv"

    def test_native_value(self):
        coord = _make_coordinator(uv_index=8)
        sensor = NeaUVSensor(coord, _make_config(), "entry1")
        assert sensor.native_value == 8

    def test_native_value_zero(self):
        coord = _make_coordinator(uv_index=0)
        sensor = NeaUVSensor(coord, _make_config(), "entry1")
        assert sensor.native_value == 0


# ---------------------------------------------------------------------------
# NeaPM25Sensor
# ---------------------------------------------------------------------------

class TestNeaPM25Sensor:
    def test_unique_id(self):
        coord = _make_coordinator()
        sensor = NeaPM25Sensor(coord, _make_config("nea"), "West", "entry1")
        assert sensor.unique_id == "nea pm25 West"

    def test_name_non_central(self):
        coord = _make_coordinator()
        sensor = NeaPM25Sensor(coord, _make_config(), "West", "entry1")
        assert sensor.name == "PM 2.5 Readings in Western Singapore"

    def test_name_central(self):
        coord = _make_coordinator()
        sensor = NeaPM25Sensor(coord, _make_config(), "Central", "entry1")
        assert sensor.name == "PM 2.5 Readings in Central Singapore"

    def test_name_east(self):
        coord = _make_coordinator()
        sensor = NeaPM25Sensor(coord, _make_config(), "East", "entry1")
        assert sensor.name == "PM 2.5 Readings in Eastern Singapore"

    def test_native_value(self):
        pm25_data = {"west": 15, "east": 18, "central": 12, "south": 10, "north": 14}
        coord = _make_coordinator(pm25_data=pm25_data)
        sensor = NeaPM25Sensor(coord, _make_config(), "West", "entry1")
        assert sensor.native_value == 15

    def test_entity_id(self):
        coord = _make_coordinator()
        sensor = NeaPM25Sensor(coord, _make_config("nea"), "North", "entry1")
        assert sensor.entity_id == "sensor.nea_pm25north"
