"""The NEA Singapore Weather API wrapper."""
from __future__ import annotations
from ast import Str
import math
from datetime import datetime, timedelta, timezone
import logging

import aiohttp

from homeassistant.components.weather import (
    ATTR_FORECAST_CONDITION,
    ATTR_FORECAST_TEMP,
    ATTR_FORECAST_TEMP_LOW,
    ATTR_FORECAST_TIME,
    ATTR_FORECAST_WIND_BEARING,
    ATTR_FORECAST_WIND_SPEED,
)

from .const import (
    PRIMARY_ENDPOINTS,
    SECONDARY_ENDPOINTS,
    FORECAST_MAP_CONDITION,
    FORECAST_ICON_MAP_CONDITION,
    HEADERS,
)

INV_FORECAST_ICON_MAP_CONDITION = dict()
for k, v in zip(
    FORECAST_ICON_MAP_CONDITION.values(), FORECAST_ICON_MAP_CONDITION.keys()
):
    INV_FORECAST_ICON_MAP_CONDITION[k] = v

_LOGGER = logging.getLogger(__name__)


def list_mean(values):
    """Function to calculate mean from list"""
    sum_values = 0
    i = 0
    for value in values:
        if value["value"] > 0:
            sum_values += value["value"]
            i += 1
    return round(sum_values / i, 2)


class NeaData:
    """Class for NEA data objects"""

    def __init__(self, url: Str, url2: Str) -> None:
        self.url = url
        self.url2 = url2
        self.date_time = (
            datetime.now(timezone(timedelta(hours=8)))
            .replace(microsecond=0)
            .isoformat()
        )
        self.response = ""
        self._params = {"date_time": self.date_time}
        self._params2 = {}
        self._headers = HEADERS
        self._resp = ""
        self._resp2 = ""

    async def async_init(self):
        """Async function to await in main loop"""
        await self.fetch_data(self.url, self.url2)
        self.response = self._resp if self._resp2 == "" else self._resp2

    async def fetch_data(self, url1: Str, url2: Str):
        """GET response from url"""
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url1, params=self._params, headers=self._headers
            ) as resp:
                self._resp = await resp.json()
                resp.raise_for_status()

                # check if data response is too short
                if resp.content_length > 100:
                    self.process_data()
                else:
                    async with session.get(
                        url2, params=self._params2, headers=self._headers
                    ) as resp2:
                        self._resp2 = await resp2.json()
                        resp2.raise_for_status()
                        self.process_secondary_data()

    def process_data(self):
        """Function intended to be replaced by subclasses to process API response"""
        return self._resp

    def process_secondary_data(self):
        """Function intended to be replaced by subclasses to process API response"""
        return self._resp2


class Forecast2hr(NeaData):
    """Class for _forecast2hr_ data"""

    def __init__(self):
        self.timestamp = ""
        self.current_condition = ""
        self.area_forecast = dict()
        NeaData.__init__(
            self,
            PRIMARY_ENDPOINTS["forecast2hr"],
            SECONDARY_ENDPOINTS["forecast2hr"]
            + str(round(datetime.utcnow().timestamp())),
        )

    def process_data(self):
        # Update data timestamp
        self.timestamp = self._resp["items"][0]["timestamp"]

        # Get most common weather condition across Singapore areas
        _current_condition_list = [
            item["forecast"] for item in self._resp["items"][0]["forecasts"]
        ]
        self.current_condition = max(
            set(_current_condition_list),
            key=_current_condition_list.count,
        )

        # Store area forecast data
        self.area_forecast = {
            forecast["area"]: forecast["forecast"]
            for forecast in self._resp["items"][0]["forecasts"]
        }

        _LOGGER.debug("%s: Data processed", self.__class__.__name__)
        return

    def process_secondary_data(self):
        # Update data timestamp
        _tmp_forecast_datetime = datetime.strptime(
            self._resp2["Channel2HrForecast"]["Item"]["ForecastIssue"]["DateTimeStr"]
            + " 2022",
            "%I.%M%p %d %b %Y",
        ).replace(tzinfo=timezone(timedelta(hours=8)))
        self.timestamp = _tmp_forecast_datetime.isoformat()

        # Get most common weather condition across Singapore areas
        _current_condition_list = [
            INV_FORECAST_ICON_MAP_CONDITION[item["Forecast"]]
            for item in self._resp2["Channel2HrForecast"]["Item"]["WeatherForecast"][
                "Area"
            ]
        ]
        self.current_condition = max(
            set(_current_condition_list),
            key=_current_condition_list.count,
        )

        # Store area forecast data
        self.area_forecast = {
            forecast["Name"]: INV_FORECAST_ICON_MAP_CONDITION[forecast["Forecast"]]
            for forecast in self._resp2["Channel2HrForecast"]["Item"][
                "WeatherForecast"
            ]["Area"]
        }

        _LOGGER.debug("%s: Secondary data processed", self.__class__.__name__)
        return


class Forecast24hr(NeaData):
    """Class for _forecast24hr_ data"""

    def __init__(self):
        self.timestamp = ""
        self.region_forecast = dict()
        NeaData.__init__(
            self,
            PRIMARY_ENDPOINTS["forecast24hr"],
            SECONDARY_ENDPOINTS["forecast24hr"]
            + str(round(datetime.utcnow().timestamp())),
        )

    def process_data(self):
        # Update data timestamp
        self.timestamp = self._resp["items"][0]["timestamp"]

        # Create region forecast
        for region in self._resp["items"][0]["periods"][0]["regions"].keys():
            self.region_forecast[region] = list()
            for period in self._resp["items"][0]["periods"]:
                _time = datetime.fromisoformat(period["time"]["start"])
                _now = datetime.now(timezone(timedelta(hours=8)))
                _day = "Today " if _time.date() == _now.date() else "Tomorrow "
                _time_of_day = (
                    "morning"
                    if _time.hour == 6
                    else "afternoon"
                    if _time.hour == 12
                    else "evening"
                )
                _condition = period["regions"][region]
                self.region_forecast[region] += [[_day + _time_of_day, _condition]]

        _LOGGER.debug("%s: Data processed", self.__class__.__name__)
        return

    def process_secondary_data(self):
        # Update data timestamp
        _tmp_forecast_datetime = datetime.strptime(
            self._resp2["Channel2HrForecast"]["Item"]["ForecastIssue"]["DateTimeStr"]
            + " 2022",
            "%I.%M%p %d %b %Y",
        ).replace(tzinfo=timezone(timedelta(hours=8)))
        self.timestamp = _tmp_forecast_datetime.isoformat()

        # Create region forecast
        for region in ["east", "west", "north", "south", "central"]:
            self.region_forecast[region] = [
                [
                    self._resp2["Channel24HrForecast"]["Forecasts"][0]["TimePeriod"],
                    INV_FORECAST_ICON_MAP_CONDITION[
                        self._resp2["Channel24HrForecast"]["Forecasts"][0][
                            "Wx" + region
                        ]
                    ],
                ]
            ]
        _LOGGER.debug("%s: Secondary data processed", self.__class__.__name__)
        return


class Forecast4day(NeaData):
    """Class for _forecast4day_ data"""

    def __init__(self):
        self.forecast = list()
        NeaData.__init__(
            self,
            PRIMARY_ENDPOINTS["forecast4day"],
            SECONDARY_ENDPOINTS["forecast4day"]
            + str(round(datetime.utcnow().timestamp())),
        )

    def process_data(self):
        # Create 4-day forecast
        self.forecast = list()
        for entry in self._resp["items"][0]["forecasts"]:
            for forecast_condition, condition in FORECAST_MAP_CONDITION.items():
                if forecast_condition in entry["forecast"].lower():
                    self.forecast.append(
                        {
                            ATTR_FORECAST_TIME: entry["timestamp"],
                            ATTR_FORECAST_TEMP: entry["temperature"]["high"],
                            ATTR_FORECAST_TEMP_LOW: entry["temperature"]["low"],
                            ATTR_FORECAST_WIND_SPEED: entry["wind"]["speed"]["high"],
                            ATTR_FORECAST_WIND_BEARING: entry["wind"]["direction"],
                            ATTR_FORECAST_CONDITION: condition,
                        }
                    )
                    break
        _LOGGER.debug("%s: Data processed", self.__class__.__name__)
        return

    def process_secondary_data(self):
        # Create 4-day forecast
        self.forecast = list()
        _today = datetime.now(timezone(timedelta(hours=8))).replace(microsecond=0)
        _date_map = dict()
        for i in range(5):
            _date = _today + timedelta(days=i)
            _date_map[_date.strftime("%a").upper()] = _date.replace(
                microsecond=0
            ).isoformat()

        for entry in self._resp2:
            for forecast_condition, condition in FORECAST_MAP_CONDITION.items():
                if forecast_condition in entry["forecast"].lower():
                    self.forecast.append(
                        {
                            ATTR_FORECAST_TIME: _date_map[entry["day"]],
                            ATTR_FORECAST_TEMP: float(entry["temperature"][-4:-2]),
                            ATTR_FORECAST_TEMP_LOW: float(entry["temperature"][:2]),
                            ATTR_FORECAST_WIND_SPEED: int(entry["wind_speed"][-6:-4]),
                            ATTR_FORECAST_WIND_BEARING: entry["wind_speed"].split(" ")[
                                0
                            ],
                            ATTR_FORECAST_CONDITION: condition,
                        }
                    )
                    break
        _LOGGER.debug("%s: Secondary data processed", self.__class__.__name__)
        return


class Temperature(NeaData):
    """Class for _temperature_ data"""

    def __init__(self):
        self.timestamp = ""
        self.temp_avg = ""
        NeaData.__init__(
            self,
            PRIMARY_ENDPOINTS["temperature"],
            SECONDARY_ENDPOINTS["temperature"],
        )

    def process_data(self):
        # Update data timestamp
        self.timestamp = self._resp["items"][0]["timestamp"]

        self.temp_avg = list_mean(self._resp["items"][0]["readings"])

        _LOGGER.debug("%s: Data processed", self.__class__.__name__)
        return

    def process_secondary_data(self):
        _LOGGER.debug("%s: Secondary data processed", self.__class__.__name__)
        return


class Humidity(NeaData):
    """Class for _humidity_ data"""

    def __init__(self):
        self.timestamp = ""
        self.humd_avg = ""
        NeaData.__init__(
            self,
            PRIMARY_ENDPOINTS["humidity"],
            SECONDARY_ENDPOINTS["humidity"],
        )

    def process_data(self):
        # Update data timestamp
        self.timestamp = self._resp["items"][0]["timestamp"]

        self.humd_avg = list_mean(self._resp["items"][0]["readings"])
        _LOGGER.debug("%s: Data processed", self.__class__.__name__)
        return

    def process_secondary_data(self):
        _LOGGER.debug("%s: Secondary data processed", self.__class__.__name__)
        return


class WindDirection(NeaData):
    """Class for _wind-direction_ data"""

    def __init__(self):
        self.timestamp = ""
        self.data = list()
        NeaData.__init__(
            self,
            PRIMARY_ENDPOINTS["wind-direction"],
            SECONDARY_ENDPOINTS["wind-direction"],
        )

    def process_data(self):
        # Update data timestamp
        self.timestamp = self._resp["items"][0]["timestamp"]

        # Store wind direction data
        self.data = self._resp["items"][0]["readings"]

        _LOGGER.debug("%s: Data processed", self.__class__.__name__)
        return

    def process_secondary_data(self):
        _LOGGER.debug("%s: Secondary data processed", self.__class__.__name__)
        return


class WindSpeed(NeaData):
    """Class for _wind-speed_ data"""

    def __init__(self):
        self.timestamp = ""
        self.data = list()
        NeaData.__init__(
            self,
            PRIMARY_ENDPOINTS["wind-speed"],
            SECONDARY_ENDPOINTS["wind-speed"],
        )

    def process_data(self):
        # Update data timestamp
        self.timestamp = self._resp["items"][0]["timestamp"]

        # Store wind speed data
        self.data = self._resp["items"][0]["readings"]

        _LOGGER.debug("%s: Data processed", self.__class__.__name__)
        return

    def process_secondary_data(self):
        _LOGGER.debug("%s: Secondary data processed", self.__class__.__name__)
        return


class Wind:
    """Special class for combining _wind-speed_ & _wind-direction_ data"""

    def __init__(self):
        self.direction = WindDirection()
        self.speed = WindSpeed()
        self.wind_status: dict
        self.wind_speed_avg: float
        self.wind_dir_avg: float
        self.response: dict

    async def async_init(self):
        """Async function to await in main loop"""
        await self.direction.async_init()
        await self.speed.async_init()
        self.response = {
            "wind_speed": self.speed.response,
            "wind_direction": self.direction.response,
        }
        self.wind_status = self.calc_wind_status(
            self.direction.data,
            self.speed.data,
        )
        self.wind_speed_avg = self.wind_status["agg_wind_speed"]
        self.wind_dir_avg = self.wind_status["agg_wind_direction"]

    def calc_wind_status(self, wind_speed, wind_direction):
        """Function to aggregate wind readings into a single aggregated value"""
        result = {
            "ns_sum": 0,
            "ns_avg": 0,
            "ew_sum": 0,
            "ew_avg": 0,
            "readings_used": 0,
            "agg_wind_speed": 0,
            "agg_wind_direction": 0,
        }
        for wind_speed_reading in wind_speed:
            for wind_direction_reading in wind_direction:
                if (
                    wind_speed_reading["station_id"]
                    == wind_direction_reading["station_id"]
                ):
                    result["ns_sum"] += wind_speed_reading["value"] * math.cos(
                        math.radians(wind_direction_reading["value"] + 180)
                    )
                    result["ew_sum"] += wind_speed_reading["value"] * math.sin(
                        math.radians(wind_direction_reading["value"] + 180)
                    )
                    result["readings_used"] += 1
        result["ns_avg"] = result["ns_sum"] / result["readings_used"]
        result["ew_avg"] = result["ew_sum"] / result["readings_used"]
        result["agg_wind_speed"] = math.sqrt(
            math.pow(result["ns_avg"], 2) + math.pow(result["ew_avg"], 2)
        )
        result["agg_wind_direction"] = math.degrees(
            math.atan2(result["ew_avg"], result["ns_avg"])
        )
        if result["agg_wind_direction"] < 0:
            result["agg_wind_direction"] += 360
        return result
