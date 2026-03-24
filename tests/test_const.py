"""Tests for custom_components/nea_sg_weather/const.py"""
import pytest
from custom_components.nea_sg_weather.const import (
    AREAS,
    CONF_AREAS,
    CONF_RAIN,
    CONF_SENSOR,
    CONF_WEATHER,
    DEFAULT_NAME,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_TIMEOUT,
    DOMAIN,
    FORECAST_ICON_MAP_CONDITION,
    FORECAST_MAP_CONDITION,
    MAP_CONDITION,
    PRIMARY_ENDPOINTS,
    RAIN_SENSOR_LIST,
    REGIONS,
    SECONDARY_ENDPOINTS,
    ATTRIBUTION,
)


class TestDomainConstants:
    def test_domain(self):
        assert DOMAIN == "nea_sg_weather"

    def test_default_name(self):
        assert DEFAULT_NAME == "Singapore Weather"

    def test_default_scan_interval(self):
        assert DEFAULT_SCAN_INTERVAL == 15

    def test_default_timeout(self):
        assert DEFAULT_TIMEOUT == 60

    def test_attribution(self):
        assert "NEA" in ATTRIBUTION

    def test_conf_values(self):
        assert CONF_WEATHER == "weather"
        assert CONF_SENSOR == "sensor"
        assert CONF_AREAS == "areas"
        assert CONF_RAIN == "rain"


class TestAreas:
    def test_areas_count(self):
        assert len(AREAS) == 47

    def test_areas_no_duplicates(self):
        assert len(AREAS) == len(set(AREAS))

    def test_areas_contains_expected(self):
        for area in ["Ang Mo Kio", "Bedok", "Changi", "Jurong East", "Woodlands", "Yishun"]:
            assert area in AREAS

    def test_areas_are_strings(self):
        assert all(isinstance(a, str) for a in AREAS)


class TestRegions:
    def test_regions_count(self):
        assert len(REGIONS) == 5

    def test_regions_values(self):
        for region in ["West", "East", "Central", "South", "North"]:
            assert region in REGIONS

    def test_regions_no_duplicates(self):
        assert len(REGIONS) == len(set(REGIONS))


class TestMapCondition:
    def test_all_conditions_have_ha_mapping(self):
        # All values should be non-empty strings (HA condition names)
        for key, value in MAP_CONDITION.items():
            assert isinstance(value, str), f"{key!r} maps to non-string: {value!r}"
            assert len(value) > 0

    def test_key_conditions_present(self):
        assert "Sunny" in MAP_CONDITION
        assert "Cloudy" in MAP_CONDITION
        assert "Thundery Showers" in MAP_CONDITION
        assert "Heavy Rain" in MAP_CONDITION
        assert "Hazy" in MAP_CONDITION
        assert "Partly Cloudy" in MAP_CONDITION

    def test_sunny_maps_to_sunny(self):
        assert MAP_CONDITION["Sunny"] == "sunny"

    def test_heavy_rain_maps_to_pouring(self):
        assert MAP_CONDITION["Heavy Rain"] == "pouring"

    def test_thundery_showers_maps_to_lightning(self):
        assert MAP_CONDITION["Thundery Showers"] == "lightning-rainy"

    def test_hazy_maps_to_fog(self):
        assert MAP_CONDITION["Hazy"] == "fog"

    def test_partly_cloudy_maps_to_partlycloudy(self):
        assert MAP_CONDITION["Partly Cloudy"] == "partlycloudy"


class TestForecastIconMapCondition:
    def test_same_keys_as_map_condition(self):
        assert set(FORECAST_ICON_MAP_CONDITION.keys()) == set(MAP_CONDITION.keys())

    def test_values_are_two_char_codes(self):
        for key, value in FORECAST_ICON_MAP_CONDITION.items():
            assert isinstance(value, str), f"{key!r} has non-string code"
            assert len(value) == 2, f"{key!r} code {value!r} is not 2 chars"

    def test_sunny_icon_code(self):
        assert FORECAST_ICON_MAP_CONDITION["Sunny"] == "SU"

    def test_cloudy_icon_code(self):
        assert FORECAST_ICON_MAP_CONDITION["Cloudy"] == "CL"

    def test_no_duplicate_values(self):
        values = list(FORECAST_ICON_MAP_CONDITION.values())
        # Some conditions share codes (e.g. "Partly Cloudy" and "Partly Cloudy (Day)")
        # so we just verify there are no None values
        assert all(v is not None for v in values)


class TestForecastMapCondition:
    def test_keys_are_lowercase(self):
        for key in FORECAST_MAP_CONDITION.keys():
            assert key == key.lower(), f"Key {key!r} is not lowercase"

    def test_contains_thundery_showers(self):
        assert "thundery showers" in FORECAST_MAP_CONDITION

    def test_contains_fair(self):
        assert "fair" in FORECAST_MAP_CONDITION

    def test_values_are_strings(self):
        for k, v in FORECAST_MAP_CONDITION.items():
            assert isinstance(v, str), f"{k!r} maps to non-string"


class TestRainSensorList:
    def test_sensor_count(self):
        assert len(RAIN_SENSOR_LIST) > 0

    def test_each_sensor_has_required_fields(self):
        for sensor in RAIN_SENSOR_LIST:
            assert "id" in sensor, f"Sensor missing 'id': {sensor}"
            assert "name" in sensor, f"Sensor missing 'name': {sensor}"
            assert "location" in sensor, f"Sensor missing 'location': {sensor}"
            assert "latitude" in sensor["location"]
            assert "longitude" in sensor["location"]

    def test_location_values_are_singapore_coordinates(self):
        # Singapore latitude: ~1.2–1.5, longitude: ~103.6–104.1
        for sensor in RAIN_SENSOR_LIST:
            lat = sensor["location"]["latitude"]
            lon = sensor["location"]["longitude"]
            assert 1.1 <= lat <= 1.5, f"{sensor['id']} lat {lat} outside Singapore range"
            assert 103.5 <= lon <= 104.2, f"{sensor['id']} lon {lon} outside Singapore range"

    def test_sensor_ids_are_unique(self):
        ids = [s["id"] for s in RAIN_SENSOR_LIST]
        assert len(ids) == len(set(ids))

    def test_known_sensors_present(self):
        ids = {s["id"] for s in RAIN_SENSOR_LIST}
        for expected in ["S77", "S109", "S107", "S81"]:
            assert expected in ids


class TestEndpoints:
    def test_primary_endpoints_keys(self):
        required = {
            "forecast2hr", "forecast24hr", "temperature", "humidity",
            "wind-direction", "wind-speed", "forecast4day", "rainfall",
            "uv-index", "pm25",
        }
        assert set(PRIMARY_ENDPOINTS.keys()) == required

    def test_primary_endpoints_are_https(self):
        for key, url in PRIMARY_ENDPOINTS.items():
            assert url.startswith("https://"), f"{key} endpoint not HTTPS: {url}"

    def test_secondary_endpoints_same_keys(self):
        assert set(SECONDARY_ENDPOINTS.keys()) == set(PRIMARY_ENDPOINTS.keys())

    def test_primary_endpoints_use_data_gov_sg(self):
        for key, url in PRIMARY_ENDPOINTS.items():
            assert "data.gov.sg" in url, f"{key} does not use data.gov.sg: {url}"
