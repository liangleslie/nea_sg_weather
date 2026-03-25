"""The NEA Singapore Weather component."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import logging

from asyncio import timeout

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_SCAN_INTERVAL,
    CONF_SENSORS,
    CONF_TIMEOUT,
    CONF_REGION,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .nea import (
    Forecast2hr,
    Forecast24hr,
    Forecast4day,
    Temperature,
    Humidity,
    Wind,
    Rain,
    UVIndex,
    PM25
)

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
    """Set up nea_sg_weather as config entry."""
    coordinator = NeaWeatherDataUpdateCoordinator(hass, config_entry)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[config_entry.entry_id] = coordinator

    _platforms = get_platforms(config_entry)["platforms"]
    await hass.config_entries.async_forward_entry_setups(config_entry, _platforms)

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


_ATTR_BY_CLASS: dict[str, str] = {
    "Forecast2hr": "forecast2hr",
    "Forecast24hr": "forecast24hr",
    "Forecast4day": "forecast4day",
    "Temperature": "temperature",
    "Humidity": "humidity",
    "Wind": "wind",
    "Rain": "rain",
    "UVIndex": "uvindex",
    "PM25": "pm25",
}


class NeaWeatherData:
    """Get the latest data from NEA API."""

    def __init__(self, hass, config_entry):
        """Initialize the data object."""
        self._hass = hass
        self._config_entry = config_entry
        self.data: self.NeaData
        self._last_data: NeaWeatherData.NeaData | None = None

    async def async_update(self) -> NeaData:
        """Get the latest data from NEA API for entities registered."""
        # Consolidate data requests to avoid redundant requests
        self.data = self.NeaData()
        _data_objects = list()
        if self._config_entry.data[CONF_WEATHER]:
            _data_objects += [
                self.data.forecast2hr,
                self.data.forecast24hr,
                self.data.forecast4day,
                self.data.temperature,
                self.data.humidity,
                self.data.wind,
                self.data.rain,
                self.data.uvindex,
                self.data.pm25
            ]
        else:
            if self._config_entry.data[CONF_SENSORS].get(CONF_AREAS, ["None"]) != [
                "None"
            ]:
                _data_objects += [self.data.forecast2hr]
            if self._config_entry.data[CONF_SENSORS].get(CONF_REGION, False):
                _data_objects += [self.data.forecast24hr]
        _data_objects = set(_data_objects)

        session = async_get_clientsession(self._hass)
        failed: list[str] = []
        for data_object in _data_objects:
            class_name = data_object.__class__.__name__
            try:
                await data_object.async_init(session)
            except Exception as err:  # noqa: BLE001
                attr = _ATTR_BY_CLASS.get(class_name)
                if self._last_data is not None and attr is not None:
                    _LOGGER.warning(
                        "%s: fetch failed (%s) — using stale data.",
                        class_name, err,
                    )
                    setattr(self.data, attr, getattr(self._last_data, attr))
                else:
                    _LOGGER.warning(
                        "%s: fetch failed (%s) — no stale data available.",
                        class_name, err,
                    )
                failed.append(class_name)

        if failed and len(failed) == len(_data_objects) and self._last_data is None:
            raise UpdateFailed(f"All data fetches failed on first attempt: {failed}")

        self._last_data = self.data
        _LOGGER.debug("Coordinator was updated at %s", self.data.query_time)
        return self.data

    class NeaData:
        """Container for Weather data"""

        def __init__(self) -> None:
            self.forecast2hr = Forecast2hr()
            self.forecast24hr = Forecast24hr()
            self.forecast4day = Forecast4day()
            self.temperature = Temperature()
            self.humidity = Humidity()
            self.uvindex = UVIndex()
            self.wind = Wind()
            self.rain = Rain()
            self.pm25 = PM25()
            self.query_time = datetime.now(timezone(timedelta(hours=8))).isoformat()
