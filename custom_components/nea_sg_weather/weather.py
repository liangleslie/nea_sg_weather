"""Support for retrieving weather data from NEA."""
from __future__ import annotations

import logging
from types import MappingProxyType
from typing import Any

from homeassistant.components.weather import WeatherEntity
from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntry
from homeassistant.const import CONF_NAME, CONF_SELECTOR, TEMP_CELSIUS
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ATTRIBUTION, DOMAIN, MAP_CONDITION

_LOGGER = logging.getLogger(__name__)


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the NEA Singapore Weather weather entity from YAML (OLD)"""
    _LOGGER.warning("Loading NEA Weather via platform config is deprecated")
    config = {CONF_SELECTOR: "WEATHER", **config}

    hass.async_create_task(
        hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_IMPORT}, data=config
        )
    )


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Add a weather entity from a config_entry."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]

    async_add_entities(
        [
            NeaWeather(coordinator, config_entry.data),
        ]
    )


class NeaWeather(CoordinatorEntity, WeatherEntity):
    """Representation of a weather condition."""

    def __init__(
        self,
        coordinator,
        config: MappingProxyType[str, Any],
    ) -> None:
        """Initialise the platform with a data instance and site."""
        super().__init__(coordinator)
        self.coordinator = coordinator
        self._name = config[CONF_NAME]

    @property
    def available(self):
        """Return if weather data is available from Dark Sky."""
        return self.coordinator.data is not None

    @property
    def attribution(self):
        """Return the attribution."""
        return ATTRIBUTION

    @property
    def unique_id(self) -> str:
        """Return unique ID."""
        return self._name

    @property
    def name(self):
        """Return the friendly name of the sensor."""
        return self._name

    @property
    def temperature(self):
        """Return the current average air temperature."""
        return round(self.coordinator.data.temperature.temp_avg, 2)

    @property
    def temperature_unit(self):
        """Return the unit of measurement."""
        return TEMP_CELSIUS

    @property
    def humidity(self):
        """Return the humidity."""
        return round(self.coordinator.data.humidity.humd_avg, 2)

    @property
    def wind_speed(self):
        """Return the wind speed."""
        return round(self.coordinator.data.wind.wind_speed_avg * 1.852, 2)

    @property
    def wind_bearing(self):
        """Return the wind bearing."""
        return round(self.coordinator.data.wind.wind_dir_avg)

    @property
    def condition(self):
        """Return the weather condition based on the most common condition across all weather stations"""
        return MAP_CONDITION.get(self.coordinator.data.forecast2hr.current_condition)

    @property
    def forecast(self):
        """Return the forecast array. Forecast API returns condition in a sentence, so we try to pick out keywords to map to a weather condition"""
        return self.coordinator.data.forecast4day.forecast

    @property
    def extra_state_attributes(self) -> dict:
        """Return dict of additional properties to attach to sensors."""
        return {"Updated at": self.coordinator.data.temperature.timestamp}

    @property
    def device_info(self) -> DeviceInfo:
        """Device info."""
        return DeviceInfo(
            default_name="Weather forecast coordinator",
            identifiers={(DOMAIN,)},  # type: ignore[arg-type]
            manufacturer="NEA Weather",
            model="data.gov.sg API Polling",
        )
