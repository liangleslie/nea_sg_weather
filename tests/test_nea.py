"""Tests for custom_components/nea_sg_weather/nea.py"""
import math
import pytest
from unittest.mock import MagicMock

from custom_components.nea_sg_weather.nea import (
    list_mean,
    Forecast2hr,
    Forecast24hr,
    Forecast4day,
    Temperature,
    Humidity,
    UVIndex,
    PM25,
    PSI,
    Wind,
    Rain,
    WindDirection,
    WindSpeed,
)


# ---------------------------------------------------------------------------
# list_mean
# ---------------------------------------------------------------------------

class TestListMean:
    def test_all_positive(self):
        values = [{"value": 10}, {"value": 20}, {"value": 30}]
        assert list_mean(values) == 20.0

    def test_skips_zero_and_negative(self):
        # Only positive values (>0) contribute
        values = [{"value": 0}, {"value": -5}, {"value": 10}, {"value": 20}]
        assert list_mean(values) == 15.0

    def test_single_value(self):
        values = [{"value": 5}]
        assert list_mean(values) == 5.0

    def test_rounds_to_two_decimals(self):
        values = [{"value": 1}, {"value": 2}]
        result = list_mean(values)
        assert result == round(result, 2)

    def test_all_zeros_raises(self):
        # Division by zero since i stays 0
        with pytest.raises(ZeroDivisionError):
            list_mean([{"value": 0}, {"value": 0}])

    def test_fractional_values(self):
        values = [{"value": 1.5}, {"value": 2.5}]
        assert list_mean(values) == 2.0


# ---------------------------------------------------------------------------
# Forecast2hr
# ---------------------------------------------------------------------------

class TestForecast2hr:
    def _make_resp(self, forecasts, metadata=None):
        if metadata is None:
            metadata = [
                {"label_location": {"latitude": str(1.375 + i * 0.01), "longitude": str(103.839 + i * 0.01)}}
                for i in range(len(forecasts))
            ]
        return {
            "data": {
                "items": [{
                    "timestamp": "2024-01-01T12:00:00+08:00",
                    "forecasts": forecasts,
                }],
                "area_metadata": metadata,
            }
        }

    def test_process_data_sets_timestamp(self):
        f = Forecast2hr()
        f._resp = self._make_resp([
            {"area": "Ang Mo Kio", "forecast": "Partly Cloudy"},
        ])
        f.process_data()
        assert f.timestamp == "2024-01-01T12:00:00+08:00"

    def test_process_data_most_common_condition(self):
        f = Forecast2hr()
        f._resp = self._make_resp([
            {"area": "Ang Mo Kio", "forecast": "Partly Cloudy"},
            {"area": "Bedok", "forecast": "Partly Cloudy"},
            {"area": "Bishan", "forecast": "Sunny"},
        ])
        f.process_data()
        assert f.current_condition == "Partly Cloudy"

    def test_process_data_area_forecast_populated(self):
        f = Forecast2hr()
        f._resp = self._make_resp([
            {"area": "Ang Mo Kio", "forecast": "Partly Cloudy"},
            {"area": "Bedok", "forecast": "Sunny"},
        ])
        f.process_data()
        assert "Ang Mo Kio" in f.area_forecast
        assert "Bedok" in f.area_forecast

    def test_process_data_forecast_value(self):
        f = Forecast2hr()
        f._resp = self._make_resp([
            {"area": "Ang Mo Kio", "forecast": "Partly Cloudy"},
        ])
        f.process_data()
        assert f.area_forecast["Ang Mo Kio"]["forecast"] == "Partly Cloudy"

    def test_process_data_location_converted_to_float(self):
        f = Forecast2hr()
        metadata = [{"label_location": {"latitude": "1.375", "longitude": "103.839"}}]
        f._resp = self._make_resp(
            [{"area": "Ang Mo Kio", "forecast": "Sunny"}],
            metadata=metadata,
        )
        f.process_data()
        loc = f.area_forecast["Ang Mo Kio"]["location"]
        assert isinstance(loc["latitude"], float)
        assert isinstance(loc["longitude"], float)
        assert loc["latitude"] == pytest.approx(1.375)
        assert loc["longitude"] == pytest.approx(103.839)

    def test_process_data_all_same_condition(self):
        f = Forecast2hr()
        f._resp = self._make_resp([
            {"area": "Area A", "forecast": "Sunny"},
            {"area": "Area B", "forecast": "Sunny"},
            {"area": "Area C", "forecast": "Sunny"},
        ])
        f.process_data()
        assert f.current_condition == "Sunny"


# ---------------------------------------------------------------------------
# Forecast24hr
# ---------------------------------------------------------------------------

class TestForecast24hr:
    def _make_resp(self, periods, timestamp="2024-01-01T00:00:00+08:00"):
        return {
            "data": {
                "records": [{
                    "timestamp": timestamp,
                    "periods": periods,
                }]
            }
        }

    def _make_period(self, start_iso, regions):
        return {
            "timePeriod": {"start": start_iso},
            "regions": {r: {"text": v} for r, v in regions.items()},
        }

    def test_process_data_sets_timestamp(self):
        f = Forecast24hr()
        period = self._make_period(
            "2024-01-01T06:00:00+08:00",
            {"west": "Partly Cloudy", "east": "Sunny", "central": "Cloudy",
             "south": "Thundery Showers", "north": "Fair"},
        )
        f._resp = self._make_resp([period])
        f.process_data()
        assert f.timestamp == "2024-01-01T00:00:00+08:00"

    def test_process_data_all_regions_present(self):
        f = Forecast24hr()
        period = self._make_period(
            "2024-01-01T06:00:00+08:00",
            {"west": "Partly Cloudy", "east": "Sunny", "central": "Cloudy",
             "south": "Thundery Showers", "north": "Fair"},
        )
        f._resp = self._make_resp([period])
        f.process_data()
        for region in ["west", "east", "central", "south", "north"]:
            assert region in f.region_forecast

    def test_process_data_region_forecast_condition(self):
        f = Forecast24hr()
        period = self._make_period(
            "2024-01-01T06:00:00+08:00",
            {"west": "Partly Cloudy", "east": "Sunny", "central": "Cloudy",
             "south": "Thundery Showers", "north": "Fair"},
        )
        f._resp = self._make_resp([period])
        f.process_data()
        assert f.region_forecast["west"][0][1] == "Partly Cloudy"
        assert f.region_forecast["east"][0][1] == "Sunny"

    def test_process_data_multiple_periods(self):
        f = Forecast24hr()
        periods = [
            self._make_period(
                "2024-01-01T06:00:00+08:00",
                {"west": "Sunny", "east": "Sunny", "central": "Sunny",
                 "south": "Sunny", "north": "Sunny"},
            ),
            self._make_period(
                "2024-01-01T12:00:00+08:00",
                {"west": "Cloudy", "east": "Cloudy", "central": "Cloudy",
                 "south": "Cloudy", "north": "Cloudy"},
            ),
        ]
        f._resp = self._make_resp(periods)
        f.process_data()
        assert len(f.region_forecast["west"]) == 2

    def test_process_data_time_of_day_labels(self):
        f = Forecast24hr()
        periods = [
            self._make_period("2024-01-01T06:00:00+08:00",
                              {"west": "A", "east": "A", "central": "A", "south": "A", "north": "A"}),
            self._make_period("2024-01-01T12:00:00+08:00",
                              {"west": "B", "east": "B", "central": "B", "south": "B", "north": "B"}),
            self._make_period("2024-01-01T18:00:00+08:00",
                              {"west": "C", "east": "C", "central": "C", "south": "C", "north": "C"}),
        ]
        f._resp = self._make_resp(periods)
        f.process_data()
        labels = [entry[0] for entry in f.region_forecast["west"]]
        # Check that the three periods use morning/afternoon/evening labels
        assert any("morning" in lbl for lbl in labels)
        assert any("afternoon" in lbl for lbl in labels)
        assert any("evening" in lbl for lbl in labels)


# ---------------------------------------------------------------------------
# Forecast4day
# ---------------------------------------------------------------------------

class TestForecast4day:
    def _make_entry(self, forecast_text, temp_high=33, temp_low=25,
                    wind_high=20, wind_low=10, wind_dir="NE"):
        return {
            "timestamp": "2024-01-02T00:00:00+08:00",
            "forecast": {"text": forecast_text},
            "temperature": {"high": temp_high, "low": temp_low},
            "wind": {"speed": {"high": wind_high, "low": wind_low}, "direction": wind_dir},
        }

    def _make_resp(self, entries):
        return {"data": {"records": [{"forecasts": entries}]}}

    def test_process_data_partly_cloudy(self):
        f = Forecast4day()
        f._resp = self._make_resp([self._make_entry("Partly cloudy with showers")])
        f.process_data()
        assert len(f.forecast) == 1
        assert f.forecast[0]["condition"] == "partlycloudy"

    def test_process_data_thundery(self):
        f = Forecast4day()
        f._resp = self._make_resp([self._make_entry("Thundery showers expected")])
        f.process_data()
        assert f.forecast[0]["condition"] == "lightning-rainy"

    def test_process_data_temperature(self):
        f = Forecast4day()
        f._resp = self._make_resp([self._make_entry("Fair", temp_high=33, temp_low=25)])
        f.process_data()
        assert f.forecast[0]["native_temperature"] == 33
        assert f.forecast[0]["native_templow"] == 25

    def test_process_data_wind_speed_is_average(self):
        f = Forecast4day()
        f._resp = self._make_resp([self._make_entry("Fair", wind_high=20, wind_low=10)])
        f.process_data()
        assert f.forecast[0]["native_wind_speed"] == pytest.approx(15.0)

    def test_process_data_wind_direction(self):
        f = Forecast4day()
        f._resp = self._make_resp([self._make_entry("Cloudy", wind_dir="SW")])
        f.process_data()
        assert f.forecast[0]["wind_bearing"] == "SW"

    def test_process_data_multiple_entries(self):
        f = Forecast4day()
        entries = [
            self._make_entry("Fair"),
            self._make_entry("Partly cloudy"),
            self._make_entry("Thundery showers"),
            self._make_entry("Cloudy"),
        ]
        f._resp = self._make_resp(entries)
        f.process_data()
        assert len(f.forecast) == 4

    def test_process_data_unknown_condition_skipped(self):
        f = Forecast4day()
        # A forecast text that matches no FORECAST_MAP_CONDITION key
        f._resp = self._make_resp([self._make_entry("Unknown bizarre weather")])
        f.process_data()
        assert len(f.forecast) == 0

    def test_process_data_timestamp_stored(self):
        f = Forecast4day()
        f._resp = self._make_resp([self._make_entry("Fair")])
        f.process_data()
        assert f.forecast[0]["datetime"] == "2024-01-02T00:00:00+08:00"


# ---------------------------------------------------------------------------
# Temperature
# ---------------------------------------------------------------------------

class TestTemperature:
    def _make_resp(self, values, timestamp="2024-01-01T12:00:00+08:00"):
        return {
            "data": {
                "readings": [{
                    "timestamp": timestamp,
                    "data": [{"value": v} for v in values],
                }]
            }
        }

    def test_process_data_timestamp(self):
        t = Temperature()
        t._resp = self._make_resp([28.0, 29.0, 30.0])
        t.process_data()
        assert t.timestamp == "2024-01-01T12:00:00+08:00"

    def test_process_data_average(self):
        t = Temperature()
        t._resp = self._make_resp([28.0, 30.0])
        t.process_data()
        assert t.temp_avg == pytest.approx(29.0)

    def test_process_data_single_station(self):
        t = Temperature()
        t._resp = self._make_resp([27.5])
        t.process_data()
        assert t.temp_avg == pytest.approx(27.5)

    def test_process_data_multiple_stations(self):
        t = Temperature()
        t._resp = self._make_resp([25.0, 26.0, 27.0, 28.0, 29.0])
        t.process_data()
        assert t.temp_avg == pytest.approx(27.0)


# ---------------------------------------------------------------------------
# Humidity
# ---------------------------------------------------------------------------

class TestHumidity:
    def _make_resp(self, values, timestamp="2024-01-01T12:00:00+08:00"):
        return {
            "data": {
                "readings": [{
                    "timestamp": timestamp,
                    "data": [{"value": v} for v in values],
                }]
            }
        }

    def test_process_data_average(self):
        h = Humidity()
        h._resp = self._make_resp([80.0, 90.0])
        h.process_data()
        assert h.humd_avg == pytest.approx(85.0)

    def test_process_data_empty_list_sets_zero(self):
        # statistics.fmean on empty list raises StatisticsError, caught -> 0
        h = Humidity()
        h._resp = self._make_resp([])
        h.process_data()
        assert h.humd_avg == 0

    def test_process_data_timestamp(self):
        h = Humidity()
        h._resp = self._make_resp([75.0])
        h.process_data()
        assert h.timestamp == "2024-01-01T12:00:00+08:00"


# ---------------------------------------------------------------------------
# UVIndex
# ---------------------------------------------------------------------------

class TestUVIndex:
    def _make_resp(self, uv_value, timestamp="2024-01-01T12:00:00+08:00"):
        return {
            "data": {
                "records": [{
                    "timestamp": timestamp,
                    "index": [{"value": uv_value}],
                }]
            }
        }

    def test_process_data_uv_index(self):
        u = UVIndex()
        u._resp = self._make_resp(7)
        u.process_data()
        assert u.uv_index == 7

    def test_process_data_timestamp(self):
        u = UVIndex()
        u._resp = self._make_resp(3, timestamp="2024-06-01T10:00:00+08:00")
        u.process_data()
        assert u.timestamp == "2024-06-01T10:00:00+08:00"

    def test_process_data_zero_uv(self):
        u = UVIndex()
        u._resp = self._make_resp(0)
        u.process_data()
        assert u.uv_index == 0

    def test_process_data_high_uv(self):
        u = UVIndex()
        u._resp = self._make_resp(12)
        u.process_data()
        assert u.uv_index == 12


# ---------------------------------------------------------------------------
# PM25
# ---------------------------------------------------------------------------

class TestPM25:
    def _make_resp(self, readings, timestamp="2024-01-01T12:00:00+08:00"):
        return {
            "data": {
                "items": [{
                    "timestamp": timestamp,
                    "readings": {
                        "pm25_one_hourly": readings,
                    },
                }]
            }
        }

    def test_process_data_stores_readings(self):
        pm = PM25()
        readings = {"west": 12, "east": 15, "central": 10, "south": 8, "north": 11}
        pm._resp = self._make_resp(readings)
        pm.process_data()
        assert pm.data == readings

    def test_process_data_timestamp(self):
        pm = PM25()
        pm._resp = self._make_resp({"west": 5})
        pm.process_data()
        assert pm.timestamp == "2024-01-01T12:00:00+08:00"

    def test_process_data_region_values(self):
        pm = PM25()
        readings = {"west": 20, "east": 25, "central": 18, "south": 22, "north": 19}
        pm._resp = self._make_resp(readings)
        pm.process_data()
        assert pm.data["west"] == 20
        assert pm.data["north"] == 19


# ---------------------------------------------------------------------------
# PSI
# ---------------------------------------------------------------------------

class TestPSI:
    _REGIONS = ("west", "east", "central", "south", "north")

    def _make_resp(
        self,
        psi,
        pm25_24h=None,
        sub_indices=None,
        timestamp="2024-01-01T12:00:00+08:00",
    ):
        readings = {"psi_twenty_four_hourly": psi}
        if pm25_24h is not None:
            readings["pm25_twenty_four_hourly"] = pm25_24h
        for pollutant, values in (sub_indices or {}).items():
            readings[f"{pollutant}_sub_index"] = values
        return {
            "data": {
                "items": [{
                    "timestamp": timestamp,
                    "readings": readings,
                }]
            }
        }

    def _readings(self, base):
        return {r: base + i for i, r in enumerate(self._REGIONS)}

    def test_process_data_stores_psi(self):
        p = PSI()
        psi = self._readings(50)
        p._resp = self._make_resp(psi)
        p.process_data()
        assert p.data == psi

    def test_process_data_timestamp(self):
        p = PSI()
        p._resp = self._make_resp(self._readings(50))
        p.process_data()
        assert p.timestamp == "2024-01-01T12:00:00+08:00"

    def test_process_data_region_values(self):
        p = PSI()
        p._resp = self._make_resp({"west": 121, "east": 95, "central": 130, "south": 88, "north": 101})
        p.process_data()
        assert p.data["central"] == 130
        assert p.data["south"] == 88

    def test_process_data_stores_pm25_24h(self):
        p = PSI()
        pm25_24h = self._readings(30)
        p._resp = self._make_resp(self._readings(50), pm25_24h=pm25_24h)
        p.process_data()
        assert p.pm25_24h == pm25_24h

    def test_process_data_missing_pm25_24h_is_empty(self):
        p = PSI()
        p._resp = self._make_resp(self._readings(50))
        p.process_data()
        assert p.pm25_24h == {}

    def test_process_data_sub_indices_keyed_by_pollutant(self):
        p = PSI()
        sub = {
            "pm25": self._readings(50),
            "pm10": self._readings(40),
            "so2": self._readings(10),
            "co": self._readings(5),
            "o3": self._readings(20),
        }
        p._resp = self._make_resp(self._readings(50), sub_indices=sub)
        p.process_data()
        assert p.sub_indices == sub
        assert set(p.sub_indices) == {"pm25", "pm10", "so2", "co", "o3"}

    def test_process_data_ignores_non_sub_index_readings(self):
        p = PSI()
        resp = self._make_resp(self._readings(50), sub_indices={"pm25": self._readings(50)})
        resp["data"]["items"][0]["readings"]["co_eight_hour_max"] = self._readings(1)
        resp["data"]["items"][0]["readings"]["no2_one_hour_max"] = self._readings(2)
        p._resp = resp
        p.process_data()
        assert set(p.sub_indices) == {"pm25"}

    def test_process_data_no_sub_indices_is_empty(self):
        p = PSI()
        p._resp = self._make_resp(self._readings(50))
        p.process_data()
        assert p.sub_indices == {}

    def test_process_data_concentrations_keyed_by_pollutant(self):
        p = PSI()
        resp = self._make_resp(self._readings(50))
        readings = resp["data"]["items"][0]["readings"]
        readings["pm25_twenty_four_hourly"] = self._readings(25)
        readings["pm10_twenty_four_hourly"] = self._readings(38)
        readings["so2_twenty_four_hourly"] = self._readings(5)
        readings["o3_eight_hour_max"] = self._readings(65)
        readings["co_eight_hour_max"] = self._readings(1)
        readings["no2_one_hour_max"] = self._readings(28)
        p._resp = resp
        p.process_data()
        assert set(p.concentrations) == {
            "pm25_24h", "pm10_24h", "so2_24h", "o3_8h", "co_8h", "no2_1h"
        }
        assert p.concentrations["pm10_24h"] == self._readings(38)
        assert p.concentrations["no2_1h"]["central"] == 30

    def test_process_data_missing_concentration_is_empty(self):
        p = PSI()
        resp = self._make_resp(self._readings(50))
        resp["data"]["items"][0]["readings"]["pm10_twenty_four_hourly"] = self._readings(38)
        p._resp = resp
        p.process_data()
        assert p.concentrations["pm10_24h"] == self._readings(38)
        assert p.concentrations["co_8h"] == {}
        assert p.data == self._readings(50)

    def test_initial_state(self):
        p = PSI()
        assert p.timestamp == ""
        assert p.data == {}
        assert p.pm25_24h == {}
        assert p.sub_indices == {}
        assert p.concentrations == {}


# ---------------------------------------------------------------------------
# Wind.calc_wind_status
# ---------------------------------------------------------------------------

class TestWindCalcStatus:
    def _wind(self):
        return Wind()

    def test_single_station_from_north(self):
        """Wind from north (0°) should produce southward result."""
        w = self._wind()
        result = w.calc_wind_status(
            wind_speed=[{"stationId": "S1", "value": 10}],
            wind_direction=[{"stationId": "S1", "value": 0}],
        )
        assert result["readings_used"] == 1
        assert result["agg_wind_speed"] == pytest.approx(10.0, rel=1e-5)
        assert result["agg_wind_direction"] == pytest.approx(180.0, abs=1e-3)

    def test_single_station_from_south(self):
        """Wind from south (180°) → agg_direction ≈ 0° (or 360°, which is equivalent)."""
        w = self._wind()
        result = w.calc_wind_status(
            wind_speed=[{"stationId": "S1", "value": 10}],
            wind_direction=[{"stationId": "S1", "value": 180}],
        )
        assert result["agg_wind_speed"] == pytest.approx(10.0, rel=1e-5)
        # 360.0 and 0.0 are equivalent bearings; floating-point may yield either
        assert result["agg_wind_direction"] % 360 == pytest.approx(0.0, abs=1e-3)

    def test_two_stations_same_direction(self):
        """Two stations same speed/direction → same avg speed."""
        w = self._wind()
        result = w.calc_wind_status(
            wind_speed=[
                {"stationId": "S1", "value": 5},
                {"stationId": "S2", "value": 5},
            ],
            wind_direction=[
                {"stationId": "S1", "value": 90},
                {"stationId": "S2", "value": 90},
            ],
        )
        assert result["readings_used"] == 2
        assert result["agg_wind_speed"] == pytest.approx(5.0, rel=1e-5)

    def test_direction_clamped_positive(self):
        """agg_wind_direction should always be in [0, 360)."""
        w = self._wind()
        result = w.calc_wind_status(
            wind_speed=[{"stationId": "S1", "value": 10}],
            wind_direction=[{"stationId": "S1", "value": 90}],
        )
        assert 0 <= result["agg_wind_direction"] < 360

    def test_mismatched_station_ids_ignored(self):
        """Station IDs that don't match produce zero wind rather than crashing."""
        w = self._wind()
        result = w.calc_wind_status(
            wind_speed=[{"stationId": "S1", "value": 10}],
            wind_direction=[{"stationId": "S99", "value": 0}],
        )
        assert result["readings_used"] == 0
        assert result["agg_wind_speed"] == 0
        assert result["agg_wind_direction"] == 0

    def test_result_contains_all_keys(self):
        w = self._wind()
        result = w.calc_wind_status(
            wind_speed=[{"stationId": "S1", "value": 5}],
            wind_direction=[{"stationId": "S1", "value": 45}],
        )
        for key in ["ns_sum", "ns_avg", "ew_sum", "ew_avg", "readings_used",
                    "agg_wind_speed", "agg_wind_direction"]:
            assert key in result

    def test_opposing_winds_cancel(self):
        """Equal-speed opposing stations produce near-zero aggregate speed."""
        w = self._wind()
        result = w.calc_wind_status(
            wind_speed=[
                {"stationId": "S1", "value": 10},
                {"stationId": "S2", "value": 10},
            ],
            wind_direction=[
                {"stationId": "S1", "value": 0},    # from north
                {"stationId": "S2", "value": 180},  # from south
            ],
        )
        assert result["agg_wind_speed"] == pytest.approx(0.0, abs=1e-9)


# ---------------------------------------------------------------------------
# Rain
# ---------------------------------------------------------------------------

class TestRain:
    def _make_resp(self, station_readings, timestamp="2024-01-01T12:00:00+08:00", stations=None):
        if stations is None:
            seen = {r["stationId"] for r in station_readings}
            stations = [
                {"id": sid, "deviceId": sid, "name": sid,
                 "location": {"latitude": 1.3, "longitude": 103.8}}
                for sid in seen
            ]
        return {
            "data": {
                "stations": stations,
                "readings": [{
                    "timestamp": timestamp,
                    "data": station_readings,
                }],
            }
        }

    def test_process_data_timestamp(self):
        r = Rain()
        r._resp = self._make_resp([{"stationId": "S77", "value": 1.2}])
        r.process_data()
        assert r.timestamp == "2024-01-01T12:00:00+08:00"

    def test_process_data_known_station_value(self):
        r = Rain()
        r._resp = self._make_resp([{"stationId": "S77", "value": 2.5}])
        r.process_data()
        assert "S77" in r.data
        assert r.data["S77"]["value"] == 2.5

    def test_process_data_missing_station_defaults_to_zero(self):
        """Stations in the station list but absent from readings should be set to 0."""
        r = Rain()
        stations = [{"id": "S77", "deviceId": "S77", "name": "Alexandra Road",
                     "location": {"latitude": 1.2937, "longitude": 103.8125}}]
        # Stations present but no readings
        r._resp = self._make_resp([], stations=stations)
        r.process_data()
        for station in r.station_list:
            assert r.data[station["id"]]["value"] == 0

    def test_process_data_station_has_name_and_location(self):
        r = Rain()
        stations = [{"id": "S77", "deviceId": "S77", "name": "Alexandra Road",
                     "location": {"latitude": 1.2937, "longitude": 103.8125}}]
        r._resp = self._make_resp([{"stationId": "S77", "value": 0.5}], stations=stations)
        r.process_data()
        assert "name" in r.data["S77"]
        assert "location" in r.data["S77"]
        assert "latitude" in r.data["S77"]["location"]
        assert "longitude" in r.data["S77"]["location"]

    def test_process_secondary_data_all_zeros(self):
        r = Rain()
        r.process_secondary_data()
        for station in r.station_list:
            assert r.data[station["id"]]["value"] == 0

    def test_process_secondary_data_all_stations_present(self):
        r = Rain()
        r.process_secondary_data()
        from custom_components.nea_sg_weather.const import RAIN_SENSOR_LIST
        for station in RAIN_SENSOR_LIST:
            assert station["id"] in r.data

    def test_process_data_all_stations_present(self):
        """Every station returned by the API should be in data after process_data."""
        r = Rain()
        stations = [
            {"id": "S77", "deviceId": "S77", "name": "Alexandra Road",
             "location": {"latitude": 1.2937, "longitude": 103.8125}},
            {"id": "S109", "deviceId": "S109", "name": "Ang Mo Kio Avenue 5",
             "location": {"latitude": 1.3764, "longitude": 103.8492}},
        ]
        r._resp = self._make_resp([], stations=stations)
        r.process_data()
        for station in stations:
            assert station["id"] in r.data


# ---------------------------------------------------------------------------
# fetch_data / async_init error handling
# ---------------------------------------------------------------------------

import asyncio as _asyncio
from unittest.mock import AsyncMock, patch, MagicMock


class TestFetchDataErrorHandling:
    """Tests for NeaData.fetch_data resilience."""

    def _mock_session(self, side_effect=None, json_data=None, status=200):
        """Return a mock aiohttp.ClientSession whose get() raises or returns data."""
        import aiohttp as _aiohttp

        if side_effect is not None:
            cm = MagicMock()
            cm.__aenter__ = AsyncMock(side_effect=side_effect)
            cm.__aexit__ = AsyncMock(return_value=False)
        else:
            resp = MagicMock()
            resp.status = status
            resp.raise_for_status = MagicMock(
                side_effect=_aiohttp.ClientResponseError(None, None, status=status)
                if status >= 400 else None
            )
            resp.json = AsyncMock(return_value=json_data or {})
            cm = MagicMock()
            cm.__aenter__ = AsyncMock(return_value=resp)
            cm.__aexit__ = AsyncMock(return_value=False)

        session = MagicMock()
        session.get = MagicMock(return_value=cm)
        return session

    async def _run(self, coro):
        return await coro

    async def test_primary_timeout_raises_when_no_secondary(self):
        """A timeout with no secondary URL should propagate as ClientError."""
        import pytest, aiohttp as _aiohttp
        from custom_components.nea_sg_weather.nea import Temperature

        t = Temperature()
        t.url2 = ""  # no secondary
        session = self._mock_session(side_effect=_asyncio.TimeoutError())

        with pytest.raises((_aiohttp.ClientError, _asyncio.TimeoutError)):
            await t.fetch_data(session, t.url, t.url2)

    async def test_primary_client_error_falls_back_to_secondary(self):
        """A ClientError on primary triggers secondary endpoint fetch for an endpoint that has one."""
        import aiohttp as _aiohttp

        from custom_components.nea_sg_weather.nea import Forecast4day

        f = Forecast4day()
        assert f.url2 != "", "Forecast4day must have a secondary URL for this test"

        call_count = 0

        class _CM:
            def __init__(self, url, **kwargs):
                self._url = url

            async def __aenter__(self):
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    raise _aiohttp.ClientError("connection refused")
                # secondary returns a minimal valid-enough response
                resp = MagicMock()
                resp.raise_for_status = MagicMock()
                resp.json = AsyncMock(return_value={"items": [{"forecasts": []}]})
                return resp

            async def __aexit__(self, *a):
                return False

        session = MagicMock()
        session.get = lambda url, **kw: _CM(url, **kw)

        # process_secondary_data is called with the minimal response; for Forecast4day
        # it iterates over an empty list, so self.forecast remains [].
        await f.fetch_data(session, f.url, f.url2)
        assert call_count == 2  # primary tried then secondary tried
        assert f.forecast == []  # secondary processed (empty, but no crash)

    async def test_both_endpoints_fail_raises(self):
        """When both primary and secondary fail, an exception is raised."""
        import aiohttp as _aiohttp, pytest
        from custom_components.nea_sg_weather.nea import Forecast2hr

        f = Forecast2hr()

        async def fake_get(url, **kwargs):
            raise _aiohttp.ClientError("network down")

        class _CM:
            def __init__(self, url, **kwargs): pass
            async def __aenter__(self): raise _aiohttp.ClientError("network down")
            async def __aexit__(self, *a): return False

        session = MagicMock()
        session.get = lambda url, **kw: _CM(url, **kw)

        with pytest.raises((_aiohttp.ClientError, _asyncio.TimeoutError)):
            await f.fetch_data(session, f.url, f.url2)


class TestWindCalcStatusZeroReadings:
    def test_zero_readings_returns_zero_wind(self):
        """calc_wind_status with no matching station pairs returns zero wind safely."""
        from custom_components.nea_sg_weather.nea import Wind
        w = Wind()
        result = w.calc_wind_status(
            wind_speed=[{"stationId": "S1", "value": 10}],
            wind_direction=[{"stationId": "S99", "value": 45}],
        )
        assert result["readings_used"] == 0
        assert result["agg_wind_speed"] == 0
        assert result["agg_wind_direction"] == 0

    def test_empty_inputs_returns_zero_wind(self):
        """calc_wind_status with empty lists returns zero wind safely."""
        from custom_components.nea_sg_weather.nea import Wind
        w = Wind()
        result = w.calc_wind_status(wind_speed=[], wind_direction=[])
        assert result["readings_used"] == 0
        assert result["agg_wind_speed"] == 0
        assert result["agg_wind_direction"] == 0


# ---------------------------------------------------------------------------
# Closest Station & Area Resolution (Zero Hardcoded Coordinates)
# ---------------------------------------------------------------------------

class TestClosestStationAndAreaResolution:
    """Verify closest-station / closest-area resolution using live API metadata."""

    BUCKLEY_LAT = 1.318114
    BUCKLEY_LON = 103.840456

    def test_temperature_uses_closest_station_from_live_metadata(self):
        t = Temperature(self.BUCKLEY_LAT, self.BUCKLEY_LON)
        t._resp = {
            "data": {
                "stations": [
                    {
                        "id": "S111",
                        "name": "Scotts Road",
                        "location": {"latitude": 1.31055, "longitude": 103.8365},
                    },
                    {
                        "id": "S60",
                        "name": "Sentosa",
                        "location": {"latitude": 1.25, "longitude": 103.8279},
                    },
                ],
                "readings": [
                    {
                        "timestamp": "2026-11-06T18:00:00+08:00",
                        "data": [
                            {"stationId": "S111", "value": 25.2},
                            {"stationId": "S60", "value": 29.8},
                        ],
                    }
                ],
            }
        }
        t.process_data()
        assert t.temp_avg == pytest.approx(25.2)
        assert t.island_temp_avg == pytest.approx(27.5)
        assert t.station_id == "S111"
        assert t.station_name == "Scotts Road"
        assert t.station_latitude == pytest.approx(1.31055)
        assert t.station_longitude == pytest.approx(103.8365)
        assert t.google_maps_url == "https://www.google.com/maps/search/?api=1&query=1.31055,103.8365"

    def test_temperature_falls_back_to_second_closest_if_closest_offline(self):
        t = Temperature(self.BUCKLEY_LAT, self.BUCKLEY_LON)
        t._resp = {
            "data": {
                "stations": [
                    {
                        "id": "S111",
                        "name": "Scotts Road",
                        "location": {"latitude": 1.31055, "longitude": 103.8365},
                    },
                    {
                        "id": "S43",
                        "name": "Kim Chuan Road",
                        "location": {"latitude": 1.3399, "longitude": 103.8878},
                    },
                ],
                "readings": [
                    {
                        "timestamp": "2026-11-06T18:00:00+08:00",
                        "data": [
                            {"stationId": "S43", "value": 26.1},
                        ],
                    }
                ],
            }
        }
        t.process_data()
        assert t.temp_avg == pytest.approx(26.1)
        assert t.station_id == "S43"
        assert t.station_name == "Kim Chuan Road"

    def test_forecast2hr_uses_closest_area_from_live_metadata(self):
        f = Forecast2hr(self.BUCKLEY_LAT, self.BUCKLEY_LON)
        f._resp = {
            "data": {
                "items": [
                    {
                        "timestamp": "2026-11-06T18:00:00+08:00",
                        "forecasts": [
                            {"area": "Novena", "forecast": "Moderate Rain"},
                            {"area": "Jurong West", "forecast": "Partly Cloudy (Day)"},
                            {"area": "Tuas", "forecast": "Partly Cloudy (Day)"},
                        ],
                    }
                ],
                "area_metadata": [
                    {"name": "Novena", "label_location": {"latitude": "1.327", "longitude": "103.826"}},
                    {"name": "Jurong West", "label_location": {"latitude": "1.34039", "longitude": "103.705"}},
                    {"name": "Tuas", "label_location": {"latitude": "1.294947", "longitude": "103.635"}},
                ],
            }
        }
        f.process_data()
        assert f.current_condition == "Moderate Rain"
        assert f.island_condition == "Partly Cloudy (Day)"
        assert f.closest_area == "Novena"

    def test_psi_and_pm25_resolve_closest_region_from_region_metadata(self):
        region_meta = [
            {"name": "north", "labelLocation": {"latitude": 1.41803, "longitude": 103.82}},
            {"name": "south", "labelLocation": {"latitude": 1.29587, "longitude": 103.82}},
            {"name": "east", "labelLocation": {"latitude": 1.35735, "longitude": 103.94}},
            {"name": "west", "labelLocation": {"latitude": 1.35735, "longitude": 103.7}},
            {"name": "central", "labelLocation": {"latitude": 1.35735, "longitude": 103.82}},
        ]
        p = PSI(self.BUCKLEY_LAT, self.BUCKLEY_LON)
        p._resp = {
            "data": {
                "regionMetadata": region_meta,
                "items": [
                    {
                        "timestamp": "2026-11-06T21:00:00+08:00",
                        "readings": {
                            "psi_twenty_four_hourly": {
                                "north": 50,
                                "south": 54,
                                "east": 58,
                                "west": 61,
                                "central": 52,
                            }
                        },
                    }
                ],
            }
        }
        p.process_data()
        assert p.closest_region == "South"
        assert p.closest_value == 54
        assert p.closest_distance_km == pytest.approx(3.36, abs=0.2)


