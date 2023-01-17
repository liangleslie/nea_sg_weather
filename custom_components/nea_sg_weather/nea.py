"""The NEA Singapore Weather API wrapper."""
from __future__ import annotations
from ast import Str
import math
from datetime import datetime, timedelta, timezone
import logging
from .weathersg import Weather

# import aiohttp

from homeassistant.components.weather import (
    ATTR_FORECAST_CONDITION,
    ATTR_FORECAST_TEMP,
    ATTR_FORECAST_TEMP_LOW,
    ATTR_FORECAST_TIME,
    ATTR_FORECAST_WIND_BEARING,
    ATTR_FORECAST_WIND_SPEED,
    ATTR_FORECAST_NATIVE_TEMP,
    ATTR_FORECAST_NATIVE_TEMP_LOW,
    ATTR_FORECAST_NATIVE_WIND_SPEED,
)

from .const import (
    PRIMARY_ENDPOINTS,
    FORECAST_MAP_CONDITION,
    FORECAST_ICON_MAP_CONDITION,
    HEADERS,
    RAIN_SENSOR_LIST,
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

    def __init__(self, weather: Weather, url: Str) -> None:
        self.weather = weather
        self.url = url
        self.date_time = (
            datetime.now(timezone(timedelta(hours=8)))
            .replace(microsecond=0)
            .isoformat()
        )
        self.response = ""
        self._params = {"date_time": self.date_time}
        self._params2 = {}
        self._headers = HEADERS
        self._resp = {}
        self._resp2 = {}

    async def async_init(self):
        """Async function to await in main loop"""
        await self.fetch_data(self.url)
        self.response = self._resp if not self._resp2 else self._resp2

    async def fetch_data(self, url1: Str):
        """GET response from url"""
        self._resp = self.weather.api.json[url1.split("/")[-1]]
        self.process_data()

        # async with aiohttp.ClientSession() as session:
        #     async with session.get(
        #         url1, params=self._params, headers=self._headers
        #     ) as resp:
        #         self._resp = await resp.json()
        #         resp.raise_for_status()

        #         # check if data response is too short
        #         _LOGGER.debug(
        #             "%s: response received, length: %s",
        #             self.__class__.__name__,
        #             len(str(self._resp)),
        #         )
        #         if len(str(self._resp)) > 120:
        #             self.process_data()
        #         else:
        #             _LOGGER.warning(
        #                 "%s: Response from %s too short",
        #                 self.__class__.__name__,
        #                 url1,
        #             )

        #             if url2 != "":
        #                 _LOGGER.warning(
        #                     "%s:  Scraping NEA website for alternative data: %s",
        #                     self.__class__.__name__,
        #                     url2,
        #                 )
        #                 async with session.get(
        #                     url2, params=self._params2, headers=self._headers
        #                 ) as resp2:
        #                     self._resp2 = await resp2.json()
        #                     resp2.raise_for_status()
        #             self.process_secondary_data()

    def process_data(self):
        """Function intended to be replaced by subclasses to process API response"""
        return self._resp

    def process_secondary_data(self):
        """Function intended to be replaced by subclasses to process API response"""
        return self._resp2


class Forecast2hr(NeaData):
    """Class for _forecast2hr_ data"""

    def __init__(self, weather: Weather) -> None:
        self.timestamp = ""
        self.current_condition = ""
        self.area_forecast = dict()
        self.metadata = list()
        NeaData.__init__(
            self,
            weather,
            PRIMARY_ENDPOINTS["forecast2hr"],
        )

    def process_data(self):
        # Update data timestamp
        _LOGGER.debug("%s: Start processing", self.__class__.__name__)
        self.timestamp = self._resp["items"][0]["timestamp"]
        self.metadata = self._resp["area_metadata"]

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
            self._resp["items"][0]["forecasts"][i]["area"]: {
                "forecast": self._resp["items"][0]["forecasts"][i]["forecast"],
                "location": {
                    "latitude": self.metadata[i]["label_location"]["latitude"],
                    "longitude": self.metadata[i]["label_location"]["longitude"],
                },
            }
            for i in range(len(self._resp["items"][0]["forecasts"]))
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

    def __init__(self, weather: Weather) -> None:
        self.timestamp = ""
        self.region_forecast = dict()
        NeaData.__init__(
            self,
            weather,
            PRIMARY_ENDPOINTS["forecast24hr"],
        )

    def process_data(self):
        # Update data timestamp
        _LOGGER.debug("%s: Start processing", self.__class__.__name__)
        self.timestamp = self._resp["items"][0]["timestamp"]

        # Create region forecast
        for region in self._resp["items"][0]["periods"][0]["regions"].keys():
            self.region_forecast[region] = list()
            for period in self._resp["items"][0]["periods"]:
                _LOGGER.warning(period["time"]["start"])
                _time = datetime.fromisoformat(period["time"]["start"])
                _now = datetime.now(timezone(timedelta(hours=8)))
                _LOGGER.warning(_now)
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
                    self._resp2["Channel24HrForecast"]["Forecasts"][i]["TimePeriod"],
                    INV_FORECAST_ICON_MAP_CONDITION[
                        self._resp2["Channel24HrForecast"]["Forecasts"][i][
                            "Wx" + region
                        ]
                    ],
                ]
                for i in range(3)
            ]
        _LOGGER.debug("%s: Secondary data processed", self.__class__.__name__)
        return


class Forecast4day(NeaData):
    """Class for _forecast4day_ data"""

    def __init__(self, weather: Weather) -> None:
        self.forecast = list()
        NeaData.__init__(
            self,
            weather,
            PRIMARY_ENDPOINTS["forecast4day"],
        )

    def process_data(self):
        # Create 4-day forecast
        _LOGGER.debug("%s: Start processing", self.__class__.__name__)
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
                            ATTR_FORECAST_NATIVE_TEMP: float(
                                entry["temperature"][-4:-2]
                            ),
                            ATTR_FORECAST_NATIVE_TEMP_LOW: float(
                                entry["temperature"][:2]
                            ),
                            ATTR_FORECAST_NATIVE_WIND_SPEED: int(
                                entry["wind_speed"][-6:-4]
                            ),
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

    def __init__(self, weather: Weather) -> None:
        self.timestamp = ""
        self.temp_avg = ""
        NeaData.__init__(
            self,
            weather,
            PRIMARY_ENDPOINTS["temperature"],
        )

    def process_data(self):
        # Update data timestamp
        _LOGGER.debug("%s: Start processing", self.__class__.__name__)
        self.timestamp = self._resp["items"][0]["timestamp"]

        self.temp_avg = list_mean(self._resp["items"][0]["readings"])

        _LOGGER.debug("%s: Data processed", self.__class__.__name__)
        return

    def process_secondary_data(self):
        _LOGGER.debug("%s: Secondary data processed", self.__class__.__name__)
        return


class Humidity(NeaData):
    """Class for _humidity_ data"""

    def __init__(self, weather: Weather) -> None:
        self.timestamp = ""
        self.humd_avg = 0
        NeaData.__init__(
            self,
            weather,
            PRIMARY_ENDPOINTS["humidity"],
        )

    def process_data(self):
        # Update data timestamp
        _LOGGER.debug("%s: Start processing", self.__class__.__name__)
        self.timestamp = self._resp["items"][0]["timestamp"]

        self.humd_avg = list_mean(self._resp["items"][0]["readings"])

        _LOGGER.debug("%s: Data processed", self.__class__.__name__)
        return

    def process_secondary_data(self):
        _LOGGER.debug("%s: Secondary data processed", self.__class__.__name__)
        return


class WindDirection(NeaData):
    """Class for _wind-direction_ data"""

    def __init__(self, weather: Weather) -> None:
        self.timestamp = ""
        self.data = list()
        NeaData.__init__(
            self,
            weather,
            PRIMARY_ENDPOINTS["wind-direction"],
        )

    def process_data(self):
        # Update data timestamp
        _LOGGER.debug("%s: Start processing", self.__class__.__name__)
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

    def __init__(self, weather: Weather) -> None:
        self.timestamp = ""
        self.data = list()
        NeaData.__init__(
            self,
            weather,
            PRIMARY_ENDPOINTS["wind-speed"],
        )

    def process_data(self):
        # Update data timestamp
        _LOGGER.debug("%s: Start processing", self.__class__.__name__)
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

    def __init__(self, weather: Weather) -> None:
        self.direction = WindDirection(weather)
        self.speed = WindSpeed(weather)
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
            self.speed.data,
            self.direction.data,
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


class Rain(NeaData):
    """Class for _rainfall_ data"""

    def __init__(self, weather: Weather) -> None:
        self.timestamp = ""
        self.data = list()
        self.metadata = list()
        self.station_list = list()
        NeaData.__init__(
            self,
            weather,
            PRIMARY_ENDPOINTS["rainfall"],
        )

    def process_data(self):
        # Update data timestamp
        _LOGGER.debug("%s: Start processing", self.__class__.__name__)
        self.timestamp = self._resp["items"][0]["timestamp"]

        # Store rainfall data
        resp_data = self._resp["items"][0]["readings"]

        self.station_list = RAIN_SENSOR_LIST
        _current_station_list = [reading["station_id"] for reading in resp_data]

        self.data = dict()

        for i, station in enumerate(self.station_list):
            station_id = station["id"]
            try:
                j = _current_station_list.index(station_id)
                self.data[station_id] = {
                    "value": resp_data[j]["value"],
                    "name": self.station_list[i]["name"],
                    "location": self.station_list[i]["location"],
                }
            except (KeyError, ValueError):
                _LOGGER.debug("%s is missing, setting values as 0", station_id)
                self.data[station_id] = {
                    "value": 0,
                    "name": self.station_list[i]["name"],
                    "location": self.station_list[i]["location"],
                }

        _LOGGER.debug("%s: Data processed", self.__class__.__name__)
        return

    def process_secondary_data(self):
        _LOGGER.debug(
            "%s: No data from data.gov.api, setting all values to 0",
            self.__class__.__name__,
        )
        self.station_list = RAIN_SENSOR_LIST
        self.data = dict()
        for i, station in enumerate(self.station_list):
            station_id = station["id"]
            self.data[station_id] = {
                "value": 0,
                "name": self.station_list[i]["name"],
                "location": self.station_list[i]["location"],
            }

        _LOGGER.debug("%s: Secondary data processed", self.__class__.__name__)
        return
