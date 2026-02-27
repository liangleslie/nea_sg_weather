"""Support for retrieving weather data from NEA."""
from __future__ import annotations

import logging
from types import MappingProxyType
from typing import Any

from homeassistant.components.weather import (
    ATTR_FORECAST_CONDITION,
    ATTR_FORECAST_NATIVE_TEMP,
    ATTR_FORECAST_NATIVE_TEMP_LOW,
    ATTR_FORECAST_NATIVE_WIND_SPEED,
    ATTR_FORECAST_TIME,
    ATTR_FORECAST_WIND_BEARING,
    Forecast,
    WeatherEntity,
    WeatherEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_NAME,
    UnitOfTemperature,
    UnitOfLength,
    UnitOfPressure,
    UnitOfSpeed,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ATTRIBUTION, DOMAIN, MAP_CONDITION

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Add a weather entity from a config_entry."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]

    async_add_entities(
        [
            NeaWeather(coordinator, config_entry.data, config_entry.entry_id),
        ]
    )


class NeaWeather(CoordinatorEntity, WeatherEntity):
    """Representation of a weather condition."""

    _attr_native_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_native_precipitation_unit = UnitOfLength.MILLIMETERS
    _attr_native_pressure_unit = UnitOfPressure.HPA
    _attr_native_wind_speed_unit = UnitOfSpeed.KNOTS
    _attr_supported_features = WeatherEntityFeature.FORECAST_DAILY

    def __init__(
        self,
        coordinator,
        config: MappingProxyType[str, Any],
        entry_id: str,
    ) -> None:
        """Initialise the platform with a data instance and site."""
        super().__init__(coordinator)
        self.coordinator = coordinator
        self._name = config[CONF_NAME]
        self._entry_id = entry_id

    @property
    def available(self):
        """Return if weather data is available"""
        return self.coordinator.data is not None

    @property
    def attribution(self):
        """Return the attribution."""
        return ATTRIBUTION

    @property
    def unique_id(self):
        """Return unique ID."""
        return self._name

    @property
    def name(self):
        """Return the friendly name of the sensor."""
        return self._name

    @property
    def native_temperature(self):
        """Return the current average air temperature."""
        return round(self.coordinator.data.temperature.temp_avg, 2)

    @property
    def uv_index(self):
        """Return the current uv index."""
        return self.coordinator.data.uvindex.uv_index

    @property
    def humidity(self):
        """Return the humidity."""
        return round(self.coordinator.data.humidity.humd_avg, 2)

    @property
    def native_wind_speed(self):
        """Return the wind speed."""
        return round(self.coordinator.data.wind.wind_speed_avg, 2)

    @property
    def wind_bearing(self):
        """Return the wind bearing."""
        return round(self.coordinator.data.wind.wind_dir_avg)

    @property
    def condition(self):
        """Return the weather condition based on the most common condition across all weather stations"""
        return MAP_CONDITION.get(self.coordinator.data.forecast2hr.current_condition)

    @property
    def extra_state_attributes(self) -> dict:
        """Return dict of additional properties to attach to sensors."""
        return {"Updated at": self.coordinator.data.temperature.timestamp}

    @property
    def device_info(self) -> DeviceInfo:
        """Device info."""
        return DeviceInfo(
            name="Weather forecast coordinator",
            identifiers={(DOMAIN, self._entry_id)},
            manufacturer="NEA Weather",
            model="data.gov.sg API Polling",
        )

    async def async_forecast_daily(self) -> list[Forecast] | None:
        """Return the daily forecast in native units.
        Only implement this method if `WeatherEntityFeature.FORECAST_DAILY` is set
        """
        forecasts = []
        for entry in self.coordinator.data.forecast4day.forecast:
            forecasts.append(
                Forecast(
                    datetime=entry[ATTR_FORECAST_TIME],
                    condition=entry[ATTR_FORECAST_CONDITION],
                    native_temperature=entry[ATTR_FORECAST_NATIVE_TEMP],
                    native_templow=entry[ATTR_FORECAST_NATIVE_TEMP_LOW],
                    native_wind_speed=entry[ATTR_FORECAST_NATIVE_WIND_SPEED],
                    wind_bearing=entry[ATTR_FORECAST_WIND_BEARING],
                )
            )
        return forecasts or None
