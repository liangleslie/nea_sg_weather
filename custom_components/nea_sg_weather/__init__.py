"""The NEA Singapore Weather component."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import logging
import asyncio

from aiohttp.client_reqrep import ClientResponse
from async_timeout import timeout
import httpx
from requests.exceptions import ConnectionError as ConnectError, HTTPError, Timeout

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_SCAN_INTERVAL,
    CONF_SENSORS,
    CONF_TIMEOUT,
    CONF_REGION,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .nea import (
    Forecast2hr,
    Forecast24hr,
    Forecast4day,
    Temperature,
    Humidity,
    Wind,
    Rain,
)

from .weathersg import Weather

from .const import (
    CONF_AREAS,
    CONF_RAIN,
    CONF_SENSOR,
    CONF_WEATHER,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_TIMEOUT,
    DOMAIN,
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
        self.weather = NeaWeatherData(hass, config_entry)
        self.update_interval = timedelta(
            minutes=config_entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        )
        self._hass = hass
        self._config_entry = config_entry
        self.data: NeaWeatherData.NeaData

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=self.update_interval,
        )

    async def _async_update_data(self) -> NeaWeatherData.NeaData:
        """Fetch data from NEA."""
        try:
            async with timeout(self.timeout):
                return await self.weather.async_update()
        except Exception as err:
            raise UpdateFailed(f"Update failed: {err}") from err


class NeaWeatherData:
    """Get the latest data from NEA API."""

    def __init__(self, hass: HomeAssistant, config_entry):
        """Initialize the data object."""
        self._hass = hass
        self._config_entry = config_entry
        self.data: self.NeaData
        self.weather: Weather

    async def async_update(self) -> NeaData:
        """Get the latest data from NEA API for entities registered."""
        # Consolidate data requests to avoid redundant requests
        self.data = await self._hass.async_add_executor_job(self.NeaData)
        _data_objects = list()
        _response = dict()
        if self._config_entry.data[CONF_WEATHER]:
            _data_objects += [
                self.data.forecast2hr,
                self.data.forecast24hr,
                self.data.forecast4day,
                self.data.temperature,
                self.data.humidity,
                self.data.wind,
                self.data.rain,
            ]
        else:
            if self._config_entry.data[CONF_SENSORS].get(CONF_AREAS, ["None"]) != [
                "None"
            ]:
                _data_objects += [self.data.forecast2hr]
            if self._config_entry.data[CONF_SENSORS].get(CONF_REGION, False):
                _data_objects += [self.data.forecast24hr]
        _data_objects = set(_data_objects)

        for data_object in _data_objects:
            await data_object.async_init()
            _response[data_object.__class__.__name__] = data_object.response

        # _LOGGER.debug("Data is: %s", _response)
        _LOGGER.debug("Coordinator was updated at %s", self.data.query_time)
        return self.data

    class NeaData:
        """Container for Weather data"""

        def __init__(self) -> None:
            self.weather = Weather()
            self.forecast2hr = Forecast2hr(self.weather)
            self.forecast24hr = Forecast24hr(self.weather)
            self.forecast4day = Forecast4day(self.weather)
            self.temperature = Temperature(self.weather)
            self.humidity = Humidity(self.weather)
            self.wind = Wind(self.weather)
            self.rain = Rain(self.weather)
            self.query_time = datetime.now(timezone(timedelta(hours=8))).isoformat()
