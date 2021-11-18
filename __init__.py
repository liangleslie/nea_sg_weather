"""The NEA Singapore Weather component."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import logging
import math
from types import MappingProxyType
from typing import Any

import aiohttp
from aiohttp.client_reqrep import ClientResponse
from async_timeout import timeout
import httpx
from requests.exceptions import ConnectionError as ConnectError, HTTPError, Timeout

from homeassistant.components.camera import _get_camera_from_entity_id
from homeassistant.components.weather import (
    ATTR_FORECAST_CONDITION,
    ATTR_FORECAST_TEMP,
    ATTR_FORECAST_TEMP_LOW,
    ATTR_FORECAST_TIME,
    ATTR_FORECAST_WIND_BEARING,
    ATTR_FORECAST_WIND_SPEED,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_SCAN_INTERVAL, CONF_SENSORS, CONF_TIMEOUT
from homeassistant.core import HomeAssistant
from homeassistant.helpers.httpx_client import get_async_client
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CONF_AREAS,
    CONF_RAIN,
    CONF_REGION,
    CONF_SENSOR,
    CONF_WEATHER,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_TIMEOUT,
    DOMAIN,
    ENDPOINTS,
    FORECAST_MAP_CONDITION,
)

_LOGGER = logging.getLogger(__name__)


def get_platforms(config_entry: ConfigEntry) -> dict:
    """Get list of platforms to be set up."""
    _platforms = {"platforms": set(), "entities": list()}
    if config_entry.data[CONF_WEATHER]:
        _platforms["platforms"].add("weather")
        _platforms["entities"].append(CONF_WEATHER)
    if config_entry.data.get(CONF_SENSOR, False):
        if config_entry.data[CONF_SENSORS].get(CONF_AREAS, ["None"]) != ["None"]:
            _platforms["platforms"].add("sensor")
            _platforms["entities"].append(CONF_AREAS)
        if config_entry.data[CONF_SENSORS].get(CONF_REGION, False):
            _platforms["platforms"].add("sensor")
            _platforms["entities"].append(CONF_REGION)
        if config_entry.data[CONF_SENSORS].get(CONF_RAIN, False):
            _platforms["platforms"].add("camera")
            _platforms["entities"].append(CONF_RAIN)

    _platforms["platforms"] = list(_platforms["platforms"])

    return _platforms


async def get_url(
    hass: HomeAssistant, url: str, url_suffix="", params=None, headers=None
) -> ClientResponse:
    """Function to make GET requests"""
    try:
        _LOGGER.debug("Fetching data from %s, with params=%s", url + url_suffix, params)
        async_client = get_async_client(hass, verify_ssl=True)
        response = await async_client.get(
            url + url_suffix, params=params, headers=headers
        )
        response.raise_for_status()
        return response.json()
    except httpx.TimeoutException:
        _LOGGER.error("Timeout making GET request from %s", url + url_suffix)
    except (httpx.RequestError, httpx.HTTPStatusError) as err:
        _LOGGER.error(
            "Error getting data from %s: %s",
            url + url_suffix,
            err,
        )


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Set up Met as config entry."""
    coordinator = NeaWeatherDataUpdateCoordinator(hass, config_entry)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[config_entry.entry_id] = coordinator

    _platforms = get_platforms(config_entry)["platforms"]
    hass.config_entries.async_setup_platforms(config_entry, _platforms)

    return True


async def async_unload_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _platforms = get_platforms(config_entry)["platforms"]
    unload_ok = await hass.config_entries.async_unload_platforms(
        config_entry, _platforms
    )

    if unload_ok:
        hass.data[DOMAIN].pop(config_entry.entry_id)

    return unload_ok


class NeaWeatherDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching Nea Weather data."""

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        """Initialize global Nea Weather data updater."""
        self.timeout = config_entry.data.get(CONF_TIMEOUT, DEFAULT_TIMEOUT)
        self.weather = NeaWeatherData(hass, self.timeout, config_entry)
        self.update_interval = timedelta(
            minutes=config_entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        )
        self._hass = hass
        self._config_entry = config_entry
        self.data: NeaWeatherData.WeatherProperties

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=self.update_interval,
        )

    async def _async_update_data(self) -> NeaWeatherData.WeatherProperties:
        """Fetch data from NEA."""
        try:
            async with timeout(self.timeout):
                return await self.weather.async_update()
        except Exception as err:
            raise UpdateFailed(f"Update failed: {err}") from err


class NeaWeatherData:
    """Get the latest data from NEA API."""

    def __init__(self, hass, timeout_seconds, config_entry):
        """Initialize the data object."""
        self._hass = hass
        self._method = "GET"
        self._timeout = timeout_seconds
        self._config_entry = config_entry
        self.raw_data = dict()
        self.data: self.WeatherProperties

    async def async_update(self) -> WeatherProperties:
        """Get the latest data from NEA API for entities registered."""
        _endpoints = dict()
        self.raw_data["date_time"] = (
            datetime.now(timezone(timedelta(hours=8)))
            .replace(microsecond=0)
            .isoformat()
        )
        for option in get_platforms(self._config_entry)["entities"]:
            for key, get_params in ENDPOINTS[option].items():
                _endpoints[key] = get_params

        for key, get_params in _endpoints.items():
            _url_suffix = (
                str(math.floor(datetime.timestamp(datetime.now()) / 300) * 300)
                if get_params["url_suffix"] == "unix time"
                else ""
            )
            _params = (
                {get_params["params"]: self.raw_data["date_time"]}
                if get_params["params"] == "iso time"
                else {}
            )
            self.raw_data[key] = await get_url(
                self._hass,
                get_params["url"],
                url_suffix=_url_suffix,
                params=_params,
                headers=get_params["headers"],
            )

        _LOGGER.debug("Data is: %s", self.raw_data)
        self.data = self.WeatherProperties(
            self._hass, self.raw_data, self._config_entry
        )
        _LOGGER.debug("Coordinator was updated at %s", self.data.query_time)
        return self.data

    class WeatherProperties:
        """Class for extracting weather properties from JSON data"""

        def __init__(
            self, hass: HomeAssistant, raw_data: dict, config_entry: ConfigEntry
        ) -> None:
            """Initialize properties class"""
            self._hass = hass
            self._config_entry = config_entry
            self.query_time = raw_data["date_time"]
            self.raw_data = raw_data
            self.raw_data_keys = set(self.raw_data.keys())

            if self.raw_data_keys.issuperset(ENDPOINTS[CONF_WEATHER].keys()):
                self.update_weather(CONF_WEATHER)
            if self.raw_data_keys.issuperset(ENDPOINTS[CONF_AREAS].keys()):
                self.update_areas("areas")
            if self.raw_data_keys.issuperset(ENDPOINTS[CONF_REGION].keys()):
                self.update_region("region")
            if self.raw_data_keys.issuperset(ENDPOINTS[CONF_RAIN].keys()):
                self.update_rain("rain")

        def update_weather(self, entity):
            """Update properties for weather entity"""
            try:
                self.temp_timestamp = self.raw_data["temperature"]["items"][0][
                    "timestamp"
                ]
                self.temp_avg = self.list_mean(
                    self.raw_data["temperature"]["items"][0]["readings"]
                )
                self.humd_timestamp = self.raw_data["humidity"]["items"][0]["timestamp"]
                self.humd_avg = self.list_mean(
                    self.raw_data["humidity"]["items"][0]["readings"]
                )
                self.wind_speed_timestamp = self.raw_data["wind-speed"]["items"][0][
                    "timestamp"
                ]
                self.wind_dir_timestamp = self.raw_data["wind-direction"]["items"][0][
                    "timestamp"
                ]
                self.wind_status_dict = self.wind_status(
                    self.raw_data["wind-speed"]["items"][0]["readings"],
                    self.raw_data["wind-direction"]["items"][0]["readings"],
                )
                self.wind_speed_avg = self.wind_status_dict["agg_wind_speed"]
                self.wind_dir_avg = self.wind_status_dict["agg_wind_direction"]

                # Get most common weather condition across Singapore areas
                self._current_condition_list = [
                    item["forecast"]
                    for item in self.raw_data["forecast2hr"]["items"][0]["forecasts"]
                ]
                self.current_condition = max(
                    set(self._current_condition_list),
                    key=self._current_condition_list.count,
                )

                # Build forecast dict object
                self.forecast = list()
                for entry in self.raw_data["forecast4day"]["items"][0]["forecasts"]:
                    for forecast_condition, condition in FORECAST_MAP_CONDITION.items():
                        if forecast_condition in entry["forecast"]:
                            self.forecast.append(
                                {
                                    ATTR_FORECAST_TIME: entry["timestamp"],
                                    ATTR_FORECAST_TEMP: entry["temperature"]["high"],
                                    ATTR_FORECAST_TEMP_LOW: entry["temperature"]["low"],
                                    ATTR_FORECAST_WIND_SPEED: entry["wind"]["speed"][
                                        "high"
                                    ],
                                    ATTR_FORECAST_WIND_BEARING: entry["wind"][
                                        "direction"
                                    ],
                                    ATTR_FORECAST_CONDITION: condition,
                                }
                            )
                            break
            except KeyError as error:
                self.exception_handler(entity, error)

        def update_areas(self, entity):
            """Update properties for area sensor entities"""
            try:
                self.area_forecast_timestamp = self.raw_data["forecast2hr"]["items"][0][
                    "timestamp"
                ]
                self.area_forecast = {
                    forecast["area"]: forecast["forecast"]
                    for forecast in self.raw_data["forecast2hr"]["items"][0][
                        "forecasts"
                    ]
                }
            except KeyError as error:
                self.exception_handler(entity, error)

        def update_region(self, entity):
            """Update properties for region sensor entities"""
            try:
                self.region_forecast_timestamp = self.raw_data["forecast24hr"]["items"][
                    0
                ]["timestamp"]
                self.region_forecast = dict()
                for region in self.raw_data["forecast24hr"]["items"][0]["periods"][0][
                    "regions"
                ].keys():
                    self.region_forecast[region] = list()
                    for period in self.raw_data["forecast24hr"]["items"][0]["periods"]:
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
                        self.region_forecast[region] += [
                            [_day + _time_of_day, _condition]
                        ]
            except KeyError as error:
                self.exception_handler(entity, error)

        def update_rain(self, entity):
            """Update properties for rain map camera entity"""
            try:
                self.rain_map_timestamp = self.raw_data["rain_map"][-1]["SortingTime"]
                self.rain_map_url = (
                    "https://www.nea.gov.sg" + self.raw_data["rain_map"][-1]["Url"]
                )
            except KeyError as error:
                self.exception_handler(entity, error)

        def exception_handler(self, entity, error):
            """Function to handle KeyError exceptions when processing response JSON"""
            _LOGGER.warning(
                "Unable to parse %s data from coordinator, this could be temporary",
                entity,
            )
            _LOGGER.debug(
                "%s: Unexpected dict key %s, %s.\nRaw data is: %s",
                entity,
                error,
                type(error),
                self.raw_data[error],
            )

        def list_mean(self, values):
            """Function to calculate mean from list"""
            sum_values = 0
            i = 0
            for value in values:
                if value["value"] > 0:
                    sum_values += value["value"]
                    i += 1
            return round(sum_values / i, 2)

        def wind_status(self, wind_speed, wind_direction) -> MappingProxyType[str, Any]:
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
