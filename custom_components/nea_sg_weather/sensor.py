"""Support for retrieving weather data from NEA."""
from __future__ import annotations

import logging
from types import MappingProxyType
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PREFIX, CONF_REGION, CONF_SENSORS
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import NeaWeatherDataUpdateCoordinator
from .const import (
    AREAS,
    CONF_AREAS,
    CONF_RAIN,
    DOMAIN,
    FORECAST_ICON_BASE_URL,
    FORECAST_ICON_MAP_CONDITION,
    REGIONS,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Add sensor entities from a config_entry."""
    coordinator: NeaWeatherDataUpdateCoordinator = hass.data[DOMAIN][
        config_entry.entry_id
    ]

    # add area sensor entities
    if "All" in config_entry.data[CONF_SENSORS][CONF_AREAS]:
        entities_list = [
            NeaAreaSensor(coordinator, config_entry.data, area) for area in AREAS
        ]
    else:
        entities_list = [
            NeaAreaSensor(coordinator, config_entry.data, area)
            for area in list(set(config_entry.data[CONF_SENSORS][CONF_AREAS]))
        ]

    # add region sensor entities
    if config_entry.data[CONF_SENSORS][CONF_REGION]:
        entities_list += [
            NeaRegionSensor(coordinator, config_entry.data, region)
            for region in REGIONS
        ]

    # add rainfall sensor entities
    if config_entry.data[CONF_SENSORS][CONF_RAIN]:
        entities_list += [
            NeaRainSensor(coordinator, config_entry.data, rain_sensor_id)
            for rain_sensor_id in coordinator.data.rain.station_list
        ]

    async_add_entities(entities_list)


class NeaAreaSensor(CoordinatorEntity, SensorEntity):
    """Implementation of a NEA Weather sensor for an area in Singapore."""

    def __init__(
        self,
        coordinator,
        config: MappingProxyType[str, Any],
        area: str,
    ) -> None:
        """Initialise area sensor with a data instance and site."""
        super().__init__(coordinator)
        self.coordinator = coordinator
        self._platform = "sensor"
        self._prefix = config[CONF_SENSORS][CONF_PREFIX]
        self._area = area
        self.entity_id = (
            (self._platform + "." + self._prefix + "_" + self._area)
            .lower()
            .replace(" ", "_")
        )

    @property
    def unique_id(self):
        """Return the unique ID."""
        return self._prefix + " " + self._area

    @property
    def name(self):
        """Return the friendly name of the sensor."""
        return self._area

    @property
    def entity_picture(self):
        """Return the entity picture url from NEA to use in the frontend"""
        return FORECAST_ICON_BASE_URL + FORECAST_ICON_MAP_CONDITION[self.state] + ".png"

    @property
    def state(self):
        """Return the weather condition."""
        return self.coordinator.data.forecast2hr.area_forecast[self._area]["forecast"]

    @property
    def extra_state_attributes(self) -> dict:
        """Return dict of additional properties to attach to sensors."""
        return {
            "Updated at": self.coordinator.data.forecast2hr.timestamp,
            "latitude": self.coordinator.data.forecast2hr.area_forecast[self._area][
                "location"
            ]["latitude"],
            "longitude": self.coordinator.data.forecast2hr.area_forecast[self._area][
                "location"
            ]["longitude"],
        }

    @property
    def device_info(self) -> DeviceInfo:
        """Device info."""
        return DeviceInfo(
            default_name="Weather forecast coordinator",
            identifiers={(DOMAIN,)},  # type: ignore[arg-type]
            manufacturer="NEA Weather",
            model="data.gov.sg API Polling",
        )


class NeaRegionSensor(CoordinatorEntity, SensorEntity):
    """Implementation of a NEA Weather sensor for a region in Singapore."""

    def __init__(
        self,
        coordinator,
        config: MappingProxyType[str, Any],
        region: str,
    ) -> None:
        """Initialise area sensor with a data instance and site."""
        super().__init__(coordinator)
        self.coordinator = coordinator
        self._platform = "sensor"
        self._prefix = config[CONF_SENSORS][CONF_PREFIX]
        self._region = region
        self.entity_id = (
            (self._platform + "." + self._prefix + "_" + self._region)
            .lower()
            .replace(" ", "_")
        )

    @property
    def unique_id(self):
        """Return the unique ID."""
        return self._prefix + " " + self._region

    @property
    def name(self):
        """Return the friendly name of the sensor."""
        return (
            ("Weather in " + self._region + "ern Singapore")
            if self._region != "Central"
            else ("Weather in " + self._region + " Singapore")
        )

    @property
    def entity_picture(self):
        """Return the entity picture url from NEA to use in the frontend"""
        return FORECAST_ICON_BASE_URL + FORECAST_ICON_MAP_CONDITION[self.state] + ".png"

    @property
    def state(self):
        """Return the weather condition."""
        return self.coordinator.data.forecast24hr.region_forecast[self._region.lower()][
            0
        ][1]

    @property
    def extra_state_attributes(self) -> dict:
        """Return dict of additional properties to attach to sensors."""
        _forecasts = {
            state[0]: state[1]
            for state in self.coordinator.data.forecast24hr.region_forecast[
                self._region.lower()
            ]
        }
        return {
            "Updated at": self.coordinator.data.forecast24hr.timestamp,
            **_forecasts,
        }

    @property
    def device_info(self) -> DeviceInfo:
        """Device info."""
        return DeviceInfo(
            default_name="Weather forecast coordinator",
            identifiers={(DOMAIN,)},  # type: ignore[arg-type]
            manufacturer="NEA Weather",
            model="data.gov.sg API Polling",
        )


class NeaRainSensor(CoordinatorEntity, SensorEntity):
    """Implementation of a NEA Weather sensor for a rainfall sensor in Singapore."""

    def __init__(
        self,
        coordinator,
        config: MappingProxyType[str, Any],
        rain_sensor_id: str,
    ) -> None:
        """Initialise area sensor with a data instance and site."""
        super().__init__(coordinator)
        self.coordinator = coordinator
        self._platform = "sensor"
        self._prefix = config[CONF_SENSORS][CONF_PREFIX]
        self._rain_sensor_id = rain_sensor_id
        self.entity_id = (
            (self._platform + "." + self._prefix + "_rainfall_" + self._rain_sensor_id)
            .lower()
            .replace(" ", "_")
        )

    @property
    def unique_id(self):
        """Return the unique ID."""
        return self._prefix + " Rainfall " + self._rain_sensor_id

    @property
    def name(self):
        """Return the friendly name of the sensor."""
        return self._rain_sensor_id

    @property
    def icon(self):
        """Return the entity picture url from NEA to use in the frontend"""
        return "mdi:weather-pouring"

    @property
    def state(self):
        """Return the weather condition."""
        return self.coordinator.data.rain.data[self._rain_sensor_id]["value"]

    @property
    def entity_picture(self):
        """Return the entity picture url to display rainfall quantity"""
        rainfall_quantity = (
            0
            if self.state == 0
            else 0.2
            if self.state < 0.35
            else 0.5
            if self.state < 0.75
            else 1
            if self.state < 1.5
            else 2
            if self.state < 2.5
            else 3
            if self.state < 3.5
            else 4
            if self.state < 4.5
            else 5
        )

        return "/local/weather/" + str(rainfall_quantity) + ".png"

    @property
    def extra_state_attributes(self) -> dict:
        """Return dict of additional properties to attach to sensors."""
        return {
            "Updated at": self.coordinator.data.rain.timestamp,
            "Location name": self.coordinator.data.rain.data[self._rain_sensor_id][
                "name"
            ],
            "latitude": self.coordinator.data.rain.data[self._rain_sensor_id][
                "location"
            ]["latitude"],
            "longitude": self.coordinator.data.rain.data[self._rain_sensor_id][
                "location"
            ]["longitude"],
        }

    @property
    def device_info(self) -> DeviceInfo:
        """Device info."""
        return DeviceInfo(
            default_name="Weather forecast coordinator",
            identifiers={(DOMAIN,)},  # type: ignore[arg-type]
            manufacturer="NEA Weather",
            model="data.gov.sg API Polling",
        )
