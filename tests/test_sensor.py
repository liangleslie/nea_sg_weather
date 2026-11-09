"""Tests for custom_components/nea_sg_weather/sensor.py entity classes."""
import pytest
from unittest.mock import MagicMock

from custom_components.nea_sg_weather.sensor import (
    NeaAreaSensor,
    NeaRegionSensor,
    NeaRainSensor,
    NeaUVSensor,
    NeaPM25Sensor,
    NeaPSISensor,
    NeaPollutantSensor,
)
from custom_components.nea_sg_weather.const import DOMAIN, FORECAST_ICON_BASE_URL


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
    uv_timestamp="2024-01-01T12:00:00+08:00",
    pm25_data=None,
    pm25_timestamp="2024-01-01T12:00:00+08:00",
    psi_data=None,
    psi_pm25_24h=None,
    psi_sub_indices=None,
    psi_concentrations=None,
    psi_timestamp="2024-01-01T12:00:00+08:00",
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
    coord.data.uvindex.timestamp = uv_timestamp
    coord.data.pm25.data = pm25_data or {"west": 12, "east": 10, "central": 8, "south": 9, "north": 11}
    coord.data.pm25.timestamp = pm25_timestamp
    coord.data.psi.data = psi_data or {"west": 55, "east": 60, "central": 52, "south": 58, "north": 50}
    coord.data.psi.pm25_24h = psi_pm25_24h or {"west": 20, "east": 22, "central": 18, "south": 21, "north": 19}
    coord.data.psi.sub_indices = psi_sub_indices if psi_sub_indices is not None else {
        "pm25": {"west": 55, "east": 60, "central": 52, "south": 58, "north": 50},
        "pm10": {"west": 30, "east": 32, "central": 28, "south": 31, "north": 29},
        "so2": {"west": 5, "east": 6, "central": 4, "south": 5, "north": 5},
        "co": {"west": 3, "east": 3, "central": 2, "south": 3, "north": 3},
        "o3": {"west": 10, "east": 12, "central": 9, "south": 11, "north": 10},
    }
    coord.data.psi.concentrations = psi_concentrations if psi_concentrations is not None else {
        "pm25_24h": {"west": 25, "east": 29, "central": 38, "south": 26, "north": 25},
        "pm10_24h": {"west": 55, "east": 53, "central": 51, "south": 38, "north": 38},
        "so2_24h": {"west": 6, "east": 5, "central": 3, "south": 3, "north": 5},
        "o3_8h": {"west": 36, "east": 34, "central": 48, "south": 31, "north": 65},
        "co_8h": {"west": 1, "east": 1, "central": 1, "south": 1, "north": 1},
        "no2_1h": {"west": 52, "east": 46, "central": 46, "south": 42, "north": 28},
    }
    coord.data.psi.timestamp = psi_timestamp
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

    def test_belongs_to_main_device(self):
        coord = _make_coordinator()
        sensor = NeaAreaSensor(coord, _make_config(), "Ang Mo Kio", "entry1")
        assert sensor._attr_has_entity_name is True
        assert sensor._attr_device_info == {"identifiers": {(DOMAIN, "entry1")}}

    def test_closest_sensor_carries_station_name_and_google_maps_url(self):
        coord = _make_coordinator(area="Novena", area_forecast_value="Moderate Rain")
        coord.data.forecast2hr.current_condition = "Moderate Rain"
        coord.data.forecast2hr.closest_area = "Novena"
        coord.data.forecast2hr.closest_area_distance_km = 1.89
        coord.data.temperature.station_id = "S111"
        coord.data.temperature.station_name = "Scotts Road"
        coord.data.temperature.station_latitude = 1.31055
        coord.data.temperature.station_longitude = 103.8365
        coord.data.temperature.station_distance_km = 0.94
        coord.data.temperature.timestamp = "2026-11-06T18:30:00+08:00"

        sensor = NeaAreaSensor(coord, _make_config("nea"), "Closest", "entry1")
        assert sensor.entity_id == "sensor.nea_closest"
        assert sensor.unique_id == "nea Closest"
        assert sensor.name == "Closest"
        assert sensor.state == "Scotts Road"
        assert sensor.entity_picture == FORECAST_ICON_BASE_URL + "RA.png"

        attrs = sensor.extra_state_attributes
        assert attrs["station_id"] == "S111"
        assert attrs["station_name"] == "Scotts Road"
        assert attrs["forecast_area"] == "Novena"
        assert attrs["forecast"] == "Moderate Rain"
        assert attrs["latitude"] == pytest.approx(1.31055)
        assert attrs["longitude"] == pytest.approx(103.8365)
        assert attrs["google_maps_url"] == "https://www.google.com/maps/search/?api=1&query=1.31055,103.8365"


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

    def test_name_from_translation_key(self):
        sensor = NeaRegionSensor(_make_coordinator(), _make_config(), "West", "entry1")
        assert sensor._attr_has_entity_name is True
        assert sensor._attr_translation_key == "forecast"

    def test_belongs_to_region_device(self):
        coord = _make_coordinator()
        sensor = NeaRegionSensor(coord, _make_config(), "West", "entry1")
        assert sensor._attr_device_info == {
            "identifiers": {(DOMAIN, "entry1_west")},
            "parent_device_id": coord.device_id,
            "translation_key": "west",
        }

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

    def test_name_uses_station_location(self):
        coord = _make_coordinator(rain_station="S77", rain_name="Alexandra Road")
        sensor = NeaRainSensor(coord, _make_config(), "S77", "entry1")
        assert sensor._attr_has_entity_name is True
        assert sensor._attr_translation_key == "rainfall"
        assert sensor._attr_translation_placeholders == {"station": "Alexandra Road"}

    def test_name_falls_back_to_station_id(self):
        coord = _make_coordinator(rain_station="S77")
        sensor = NeaRainSensor(coord, _make_config(), "S99", "entry1")
        assert sensor._attr_translation_placeholders == {"station": "S99"}

    def test_belongs_to_main_device(self):
        sensor = NeaRainSensor(_make_coordinator(), _make_config(), "S77", "entry1")
        assert sensor._attr_device_info == {"identifiers": {(DOMAIN, "entry1")}}

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

    def test_available_when_station_in_data(self):
        coord = _make_coordinator(rain_station="S77")
        coord.last_update_success = True
        sensor = NeaRainSensor(coord, _make_config(), "S77", "entry1")
        assert sensor.available is True

    def test_available_false_when_station_missing_from_data(self):
        coord = _make_coordinator(rain_station="S77")
        coord.last_update_success = True
        sensor = NeaRainSensor(coord, _make_config(), "S99", "entry1")
        # S99 is not in rain.data (only S77 is), so sensor should be unavailable
        assert sensor.available is False


# ---------------------------------------------------------------------------
# NeaUVSensor
# ---------------------------------------------------------------------------

class TestNeaUVSensor:
    def test_unique_id(self):
        coord = _make_coordinator()
        sensor = NeaUVSensor(coord, _make_config("nea"), "entry1")
        assert sensor.unique_id == "nea_uv"

    def test_name_from_translation_key(self):
        sensor = NeaUVSensor(_make_coordinator(), _make_config(), "entry1")
        assert sensor._attr_has_entity_name is True
        assert sensor._attr_translation_key == "uv_index"

    def test_belongs_to_main_device(self):
        sensor = NeaUVSensor(_make_coordinator(), _make_config(), "entry1")
        assert sensor._attr_device_info == {"identifiers": {(DOMAIN, "entry1")}}

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

    def test_extra_state_attributes_uses_uv_timestamp(self):
        coord = _make_coordinator(
            uv_timestamp="2024-06-01T14:00:00+08:00",
            region_timestamp="2024-06-01T06:00:00+08:00",
        )
        sensor = NeaUVSensor(coord, _make_config(), "entry1")
        assert sensor.extra_state_attributes["Updated at"] == "2024-06-01T14:00:00+08:00"


# ---------------------------------------------------------------------------
# NeaPM25Sensor
# ---------------------------------------------------------------------------

class TestNeaPM25Sensor:
    def test_unique_id(self):
        coord = _make_coordinator()
        sensor = NeaPM25Sensor(coord, _make_config("nea"), "West", "entry1")
        assert sensor.unique_id == "nea pm25 West"

    def test_name_from_translation_key(self):
        sensor = NeaPM25Sensor(_make_coordinator(), _make_config(), "West", "entry1")
        assert sensor._attr_has_entity_name is True
        assert sensor._attr_translation_key == "pm25_1h"

    def test_belongs_to_region_device(self):
        coord = _make_coordinator()
        sensor = NeaPM25Sensor(coord, _make_config(), "West", "entry1")
        assert sensor._attr_device_info == {
            "identifiers": {(DOMAIN, "entry1_west")},
            "parent_device_id": coord.device_id,
            "translation_key": "west",
        }

    def test_native_value(self):
        pm25_data = {"west": 15, "east": 18, "central": 12, "south": 10, "north": 14}
        coord = _make_coordinator(pm25_data=pm25_data)
        sensor = NeaPM25Sensor(coord, _make_config(), "West", "entry1")
        assert sensor.native_value == 15

    def test_entity_id(self):
        coord = _make_coordinator()
        sensor = NeaPM25Sensor(coord, _make_config("nea"), "North", "entry1")
        assert sensor.entity_id == "sensor.nea_pm25north"

    def test_extra_state_attributes_uses_pm25_timestamp(self):
        coord = _make_coordinator(
            pm25_timestamp="2024-06-01T14:00:00+08:00",
            region_timestamp="2024-06-01T06:00:00+08:00",
        )
        sensor = NeaPM25Sensor(coord, _make_config(), "West", "entry1")
        assert sensor.extra_state_attributes["Updated at"] == "2024-06-01T14:00:00+08:00"


# ---------------------------------------------------------------------------
# NeaPSISensor
# ---------------------------------------------------------------------------

class TestNeaPSISensor:
    def test_unique_id(self):
        coord = _make_coordinator()
        sensor = NeaPSISensor(coord, _make_config("nea"), "West", "entry1")
        assert sensor.unique_id == "nea psi West"

    def test_name_from_translation_key(self):
        sensor = NeaPSISensor(_make_coordinator(), _make_config(), "West", "entry1")
        assert sensor._attr_has_entity_name is True
        assert sensor._attr_translation_key == "psi_24h"

    def test_belongs_to_region_device(self):
        coord = _make_coordinator()
        sensor = NeaPSISensor(coord, _make_config(), "West", "entry1")
        assert sensor._attr_device_info == {
            "identifiers": {(DOMAIN, "entry1_west")},
            "parent_device_id": coord.device_id,
            "translation_key": "west",
        }

    def test_native_value(self):
        psi_data = {"west": 121, "east": 95, "central": 130, "south": 88, "north": 101}
        coord = _make_coordinator(psi_data=psi_data)
        sensor = NeaPSISensor(coord, _make_config(), "Central", "entry1")
        assert sensor.native_value == 130

    def test_entity_id(self):
        coord = _make_coordinator()
        sensor = NeaPSISensor(coord, _make_config("nea"), "North", "entry1")
        assert sensor.entity_id == "sensor.nea_psinorth"

    def test_entity_id_prefix_with_space(self):
        coord = _make_coordinator()
        sensor = NeaPSISensor(coord, _make_config("Singapore Weather"), "West", "entry1")
        assert sensor.entity_id == "sensor.singapore_weather_psiwest"

    def test_device_class_is_aqi_without_unit(self):
        coord = _make_coordinator()
        sensor = NeaPSISensor(coord, _make_config(), "West", "entry1")
        # HA requires AQI sensors to have no unit of measurement
        assert sensor._attr_device_class == "aqi"
        assert sensor._attr_state_class == "measurement"
        assert getattr(sensor, "_attr_native_unit_of_measurement", None) is None

    def test_extra_state_attributes_timestamp_and_pm25(self):
        coord = _make_coordinator(
            psi_pm25_24h={"west": 33, "east": 22, "central": 44, "south": 21, "north": 19},
            psi_timestamp="2024-06-01T08:00:00+08:00",
        )
        sensor = NeaPSISensor(coord, _make_config(), "Central", "entry1")
        attrs = sensor.extra_state_attributes
        assert attrs["Updated at"] == "2024-06-01T08:00:00+08:00"
        assert attrs["PM2.5 (24h)"] == 44

    def test_extra_state_attributes_sub_indices(self):
        coord = _make_coordinator(
            psi_sub_indices={
                "pm25": {"west": 55, "east": 60, "central": 52, "south": 58, "north": 50},
                "so2": {"west": 5, "east": 6, "central": 4, "south": 5, "north": 5},
            }
        )
        sensor = NeaPSISensor(coord, _make_config(), "East", "entry1")
        attrs = sensor.extra_state_attributes
        assert attrs["PM25 sub-index"] == 60
        assert attrs["SO2 sub-index"] == 6
        assert "PM10 sub-index" not in attrs

    def test_extra_state_attributes_missing_region_is_none(self):
        coord = _make_coordinator(
            psi_pm25_24h={"west": 33},
            psi_sub_indices={"pm25": {"west": 55}},
        )
        sensor = NeaPSISensor(coord, _make_config(), "North", "entry1")
        attrs = sensor.extra_state_attributes
        assert attrs["PM2.5 (24h)"] is None
        assert attrs["PM25 sub-index"] is None

    def test_extra_state_attributes_no_sub_indices(self):
        coord = _make_coordinator(psi_sub_indices={})
        sensor = NeaPSISensor(coord, _make_config(), "West", "entry1")
        attrs = sensor.extra_state_attributes
        assert set(attrs) == {"Updated at", "PM2.5 (24h)"}


# ---------------------------------------------------------------------------
# NeaPollutantSensor
# ---------------------------------------------------------------------------

class TestNeaPollutantSensor:
    def test_unique_id(self):
        sensor = NeaPollutantSensor(_make_coordinator(), _make_config("nea"), "pm10_24h", "West", "entry1")
        assert sensor.unique_id == "nea pm10_24h West"

    def test_entity_id(self):
        sensor = NeaPollutantSensor(_make_coordinator(), _make_config("nea"), "pm10_24h", "North", "entry1")
        assert sensor.entity_id == "sensor.nea_pm10_24h_north"

    def test_entity_id_does_not_collide_with_hourly_pm25(self):
        coord = _make_coordinator()
        hourly = NeaPM25Sensor(coord, _make_config("nea"), "Central", "entry1")
        daily = NeaPollutantSensor(coord, _make_config("nea"), "pm25_24h", "Central", "entry1")
        assert hourly.entity_id == "sensor.nea_pm25central"
        assert daily.entity_id == "sensor.nea_pm25_24h_central"
        assert hourly.unique_id != daily.unique_id

    def test_name_from_translation_key(self):
        sensor = NeaPollutantSensor(_make_coordinator(), _make_config(), "no2_1h", "West", "entry1")
        assert sensor._attr_has_entity_name is True
        assert sensor._attr_translation_key == "no2_1h"

    def test_disabled_by_default(self):
        sensor = NeaPollutantSensor(_make_coordinator(), _make_config(), "pm10_24h", "West", "entry1")
        assert sensor._attr_entity_registry_enabled_default is False

    def test_belongs_to_region_device(self):
        coord = _make_coordinator()
        sensor = NeaPollutantSensor(coord, _make_config(), "pm10_24h", "East", "entry1")
        assert sensor._attr_device_info == {
            "identifiers": {(DOMAIN, "entry1_east")},
            "parent_device_id": coord.device_id,
            "translation_key": "east",
        }

    @pytest.mark.parametrize(
        "pollutant, device_class, unit",
        [
            ("pm25_24h", "pm25", "μg/m³"),
            ("pm10_24h", "pm10", "μg/m³"),
            ("so2_24h", "sulphur_dioxide", "μg/m³"),
            ("o3_8h", "ozone", "μg/m³"),
            ("co_8h", "carbon_monoxide", "mg/m³"),
            ("no2_1h", "nitrogen_dioxide", "μg/m³"),
        ],
    )
    def test_device_class_and_unit(self, pollutant, device_class, unit):
        sensor = NeaPollutantSensor(_make_coordinator(), _make_config(), pollutant, "West", "entry1")
        assert sensor._attr_device_class == device_class
        assert sensor._attr_native_unit_of_measurement == unit
        assert sensor._attr_state_class == "measurement"

    def test_native_value(self):
        sensor = NeaPollutantSensor(_make_coordinator(), _make_config(), "no2_1h", "Central", "entry1")
        assert sensor.native_value == 46

    def test_native_value_co(self):
        coord = _make_coordinator(psi_concentrations={"co_8h": {"west": 0.6}})
        sensor = NeaPollutantSensor(coord, _make_config(), "co_8h", "West", "entry1")
        assert sensor.native_value == 0.6

    def test_available_when_region_present(self):
        coord = _make_coordinator()
        coord.last_update_success = True
        sensor = NeaPollutantSensor(coord, _make_config(), "pm10_24h", "West", "entry1")
        assert sensor.available is True

    def test_unavailable_when_pollutant_missing(self):
        coord = _make_coordinator(psi_concentrations={"pm10_24h": {}})
        coord.last_update_success = True
        sensor = NeaPollutantSensor(coord, _make_config(), "pm10_24h", "West", "entry1")
        assert sensor.available is False
        sensor2 = NeaPollutantSensor(coord, _make_config(), "co_8h", "West", "entry1")
        assert sensor2.available is False

    def test_extra_state_attributes_timestamp(self):
        coord = _make_coordinator(psi_timestamp="2024-06-01T08:00:00+08:00")
        sensor = NeaPollutantSensor(coord, _make_config(), "pm10_24h", "West", "entry1")
        assert sensor.extra_state_attributes == {"Updated at": "2024-06-01T08:00:00+08:00"}
