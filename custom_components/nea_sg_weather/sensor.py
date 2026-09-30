"""Support for retrieving weather data from NEA."""
from __future__ import annotations

import logging
from types import MappingProxyType
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_PREFIX,
    CONF_REGION,
    CONF_SENSORS,
    UnitOfDensity,
    UnitOfPrecipitationDepth,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import NeaWeatherDataUpdateCoordinator
from .entity import main_device_info, region_device_info
from .const import (
    AREAS,
    CONF_AREAS,
    CONF_RAIN,
    DOMAIN,
    FORECAST_ICON_BASE_URL,
    FORECAST_ICON_MAP_CONDITION,
    POLLUTANT_READINGS,
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
    entry_id = config_entry.entry_id

    # add area sensor entities
    if "All" in config_entry.data[CONF_SENSORS][CONF_AREAS]:
        entities_list = [
            NeaAreaSensor(coordinator, config_entry.data, area, entry_id) for area in AREAS
        ]
    else:
        entities_list = [
            NeaAreaSensor(coordinator, config_entry.data, area, entry_id)
            for area in list(set(config_entry.data[CONF_SENSORS][CONF_AREAS]))
        ]

    # add region sensor entities
    if config_entry.data[CONF_SENSORS][CONF_REGION]:
        entities_list += [
            NeaRegionSensor(coordinator, config_entry.data, region, entry_id)
            for region in REGIONS
        ]

    # add rainfall sensor entities
    if config_entry.data[CONF_SENSORS][CONF_RAIN]:
        _known_rain_ids: set[str] = {s["id"] for s in coordinator.data.rain.station_list}
        prefix = config_entry.data[CONF_SENSORS][CONF_PREFIX]

        # Remove orphaned rain sensor entities from previous installs whose
        # station IDs are no longer present in the current API response.
        ent_reg = er.async_get(hass)
        _rainfall_prefix = f"{prefix} Rainfall "
        for entry in er.async_entries_for_config_entry(ent_reg, entry_id):
            if entry.unique_id.startswith(_rainfall_prefix):
                sid = entry.unique_id[len(_rainfall_prefix):]
                if sid not in _known_rain_ids:
                    ent_reg.async_remove(entry.entity_id)
                    _LOGGER.debug("Removed orphaned rain sensor on startup: %s", sid)

        entities_list += [
            NeaRainSensor(coordinator, config_entry.data, sid, entry_id)
            for sid in _known_rain_ids
        ]

        def _make_rain_listener(
            known: set[str],
            add_cb: AddEntitiesCallback,
        ):
            def _listener():
                current = {s["id"] for s in coordinator.data.rain.station_list}
                removed = known - current
                added = current - known

                if removed:
                    ent_reg = er.async_get(hass)
                    for sid in removed:
                        unique_id = f"{prefix} Rainfall {sid}"
                        entity_id = ent_reg.async_get_entity_id("sensor", DOMAIN, unique_id)
                        if entity_id:
                            ent_reg.async_remove(entity_id)
                            _LOGGER.debug("Removed orphaned rain sensor: %s", sid)
                    known.difference_update(removed)

                if added:
                    new_entities = [
                        NeaRainSensor(coordinator, config_entry.data, sid, entry_id)
                        for sid in added
                    ]
                    add_cb(new_entities)
                    _LOGGER.debug("Added new rain sensors: %s", added)
                    known.update(added)

            return _listener

        config_entry.async_on_unload(
            coordinator.async_add_listener(
                _make_rain_listener(_known_rain_ids, async_add_entities)
            )
        )

    # add uv sensor entities
    entities_list += [
        NeaUVSensor(coordinator, config_entry.data, entry_id)
    ]

    # add pm25 sensor entities
    if config_entry.data[CONF_SENSORS][CONF_REGION]:
        entities_list += [
            NeaPM25Sensor(coordinator, config_entry.data, region, entry_id)
            for region in REGIONS
        ]

    # add psi sensor entities
    if config_entry.data[CONF_SENSORS][CONF_REGION]:
        entities_list += [
            NeaPSISensor(coordinator, config_entry.data, region, entry_id)
            for region in REGIONS
        ]

    # add pollutant concentration sensor entities
    if config_entry.data[CONF_SENSORS][CONF_REGION]:
        entities_list += [
            NeaPollutantSensor(coordinator, config_entry.data, pollutant, region, entry_id)
            for pollutant in POLLUTANT_READINGS
            for region in REGIONS
        ]

    # Remove sensors this configuration no longer creates (areas dropped, or
    # regions or rain switched off in the reconfigure flow) so they do not stay
    # behind as orphans. Rain stations that disappear at runtime are handled by
    # the listener above.
    keep_unique_ids = {entity.unique_id for entity in entities_list}
    ent_reg = er.async_get(hass)
    for reg_entry in er.async_entries_for_config_entry(ent_reg, entry_id):
        if reg_entry.domain == "sensor" and reg_entry.unique_id not in keep_unique_ids:
            ent_reg.async_remove(reg_entry.entity_id)
            _LOGGER.debug("Removed sensor no longer configured: %s", reg_entry.entity_id)

    async_add_entities(entities_list)


class NeaAreaSensor(CoordinatorEntity, SensorEntity):
    """Implementation of a NEA Weather sensor for an area in Singapore."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator,
        config: MappingProxyType[str, Any],
        area: str,
        entry_id: str,
    ) -> None:
        """Initialise area sensor with a data instance and site."""
        super().__init__(coordinator)
        self.coordinator = coordinator
        self._platform = "sensor"
        self._prefix = config[CONF_SENSORS][CONF_PREFIX]
        self._area = area
        self._entry_id = entry_id
        self._attr_device_info = main_device_info(entry_id)
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
        return FORECAST_ICON_BASE_URL + FORECAST_ICON_MAP_CONDITION.get(self.state, "NA") + ".png"

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


class NeaRegionSensor(CoordinatorEntity, SensorEntity):
    """Implementation of a NEA Weather sensor for a region in Singapore."""

    _attr_has_entity_name = True
    _attr_translation_key = "forecast"

    def __init__(
        self,
        coordinator,
        config: MappingProxyType[str, Any],
        region: str,
        entry_id: str,
    ) -> None:
        """Initialise area sensor with a data instance and site."""
        super().__init__(coordinator)
        self.coordinator = coordinator
        self._platform = "sensor"
        self._prefix = config[CONF_SENSORS][CONF_PREFIX]
        self._region = region
        self._entry_id = entry_id
        self._attr_device_info = region_device_info(coordinator, entry_id, region)
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
    def entity_picture(self):
        """Return the entity picture url from NEA to use in the frontend"""
        return FORECAST_ICON_BASE_URL + FORECAST_ICON_MAP_CONDITION.get(self.state, "NA") + ".png"

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


class NeaPM25Sensor(CoordinatorEntity, SensorEntity):
    """Implementation of a NEA pm25 sensor for a region in Singapore."""

    _attr_has_entity_name = True
    _attr_translation_key = "pm25_1h"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_device_class = SensorDeviceClass.PM25
    _attr_native_unit_of_measurement = UnitOfDensity.MICROGRAMS_PER_CUBIC_METER

    def __init__(
        self,
        coordinator,
        config: MappingProxyType[str, Any],
        region: str,
        entry_id: str,
    ) -> None:
        """Initialise area sensor with a data instance and site."""
        super().__init__(coordinator)
        self.coordinator = coordinator
        self._platform = "sensor"
        self._prefix = config[CONF_SENSORS][CONF_PREFIX]
        self._region = region
        self._entry_id = entry_id
        self._attr_device_info = region_device_info(coordinator, entry_id, region)
        self.entity_id = (
            (self._platform + "." + self._prefix + "_pm25" + self._region)
            .lower()
            .replace(" ", "_")
        )

    @property
    def unique_id(self):
        """Return the unique ID."""
        return self._prefix + " pm25 " + self._region

    @property
    def native_value(self):
        """Return the PM2.5 reading."""
        return self.coordinator.data.pm25.data[self._region.lower()]

    @property
    def extra_state_attributes(self) -> dict:
        """Return dict of additional properties to attach to sensors."""
        return {
            "Updated at": self.coordinator.data.pm25.timestamp,
        }


class NeaPSISensor(CoordinatorEntity, SensorEntity):
    """Implementation of a NEA 24-hour PSI sensor for a region in Singapore."""

    _attr_has_entity_name = True
    _attr_translation_key = "psi_24h"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_device_class = SensorDeviceClass.AQI
    _attr_icon = "mdi:weather-hazy"

    def __init__(
        self,
        coordinator,
        config: MappingProxyType[str, Any],
        region: str,
        entry_id: str,
    ) -> None:
        """Initialise PSI sensor with a data instance and region."""
        super().__init__(coordinator)
        self.coordinator = coordinator
        self._platform = "sensor"
        self._prefix = config[CONF_SENSORS][CONF_PREFIX]
        self._region = region
        self._entry_id = entry_id
        self._attr_device_info = region_device_info(coordinator, entry_id, region)
        self.entity_id = (
            (self._platform + "." + self._prefix + "_psi" + self._region)
            .lower()
            .replace(" ", "_")
        )

    @property
    def unique_id(self):
        """Return the unique ID."""
        return self._prefix + " psi " + self._region

    @property
    def native_value(self):
        """Return the 24-hour PSI reading."""
        return self.coordinator.data.psi.data[self._region.lower()]

    @property
    def extra_state_attributes(self) -> dict:
        """Return dict of additional properties to attach to sensors."""
        psi = self.coordinator.data.psi
        region = self._region.lower()
        attributes = {
            "Updated at": psi.timestamp,
            "PM2.5 (24h)": psi.pm25_24h.get(region),
        }
        for pollutant, values in psi.sub_indices.items():
            attributes[pollutant.upper() + " sub-index"] = values.get(region)
        return attributes


# Device class and unit per pollutant; NEA reports CO in mg/m³, the rest in µg/m³
POLLUTANT_DEVICE_CLASSES = {
    "pm25_24h": SensorDeviceClass.PM25,
    "pm10_24h": SensorDeviceClass.PM10,
    "so2_24h": SensorDeviceClass.SULPHUR_DIOXIDE,
    "o3_8h": SensorDeviceClass.OZONE,
    "co_8h": SensorDeviceClass.CO,
    "no2_1h": SensorDeviceClass.NITROGEN_DIOXIDE,
}
POLLUTANT_UNITS = {
    "co_8h": UnitOfDensity.MILLIGRAMS_PER_CUBIC_METER,
}


class NeaPollutantSensor(CoordinatorEntity, SensorEntity):
    """Implementation of a NEA pollutant concentration sensor for a region in Singapore.

    One entity per pollutant in POLLUTANT_READINGS and region, reading the
    concentrations that come with the PSI response. Disabled by default so
    existing installs are not flooded with entities.
    """

    _attr_has_entity_name = True
    _attr_entity_registry_enabled_default = False
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        coordinator,
        config: MappingProxyType[str, Any],
        pollutant: str,
        region: str,
        entry_id: str,
    ) -> None:
        """Initialise pollutant sensor with a data instance, pollutant and region."""
        super().__init__(coordinator)
        self.coordinator = coordinator
        self._platform = "sensor"
        self._prefix = config[CONF_SENSORS][CONF_PREFIX]
        self._pollutant = pollutant
        self._region = region
        self._entry_id = entry_id
        self._attr_translation_key = pollutant
        self._attr_device_class = POLLUTANT_DEVICE_CLASSES[pollutant]
        self._attr_native_unit_of_measurement = POLLUTANT_UNITS.get(
            pollutant, UnitOfDensity.MICROGRAMS_PER_CUBIC_METER
        )
        self._attr_device_info = region_device_info(coordinator, entry_id, region)
        self.entity_id = (
            (self._platform + "." + self._prefix + "_" + pollutant + "_" + region)
            .lower()
            .replace(" ", "_")
        )

    @property
    def unique_id(self):
        """Return the unique ID."""
        return self._prefix + " " + self._pollutant + " " + self._region

    @property
    def available(self) -> bool:
        """Return False if the API response has no reading for this region."""
        return (
            super().available
            and self._region.lower()
            in self.coordinator.data.psi.concentrations.get(self._pollutant, {})
        )

    @property
    def native_value(self):
        """Return the pollutant concentration."""
        return self.coordinator.data.psi.concentrations[self._pollutant][
            self._region.lower()
        ]

    @property
    def extra_state_attributes(self) -> dict:
        """Return dict of additional properties to attach to sensors."""
        return {
            "Updated at": self.coordinator.data.psi.timestamp,
        }


class NeaRainSensor(CoordinatorEntity, SensorEntity):
    """Implementation of a NEA Weather sensor for a rainfall sensor in Singapore."""

    _attr_has_entity_name = True
    _attr_translation_key = "rainfall"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_device_class = SensorDeviceClass.PRECIPITATION
    _attr_native_unit_of_measurement = UnitOfPrecipitationDepth.MILLIMETERS

    def __init__(
        self,
        coordinator,
        config: MappingProxyType[str, Any],
        rain_sensor_id: str,
        entry_id: str,
    ) -> None:
        """Initialise area sensor with a data instance and site."""
        super().__init__(coordinator)
        self.coordinator = coordinator
        self._platform = "sensor"
        self._prefix = config[CONF_SENSORS][CONF_PREFIX]
        self._rain_sensor_id = rain_sensor_id
        self._entry_id = entry_id
        self._attr_device_info = main_device_info(entry_id)
        station = coordinator.data.rain.data.get(rain_sensor_id, {})
        self._attr_translation_placeholders = {
            "station": station.get("name", rain_sensor_id)
        }
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
    def available(self) -> bool:
        """Return False if this station is no longer in the API data."""
        return (
            super().available
            and self._rain_sensor_id in self.coordinator.data.rain.data
        )

    @property
    def icon(self):
        """Return the entity picture url from NEA to use in the frontend"""
        return "mdi:weather-pouring"

    @property
    def native_value(self):
        """Return the rainfall amount."""
        return self.coordinator.data.rain.data[self._rain_sensor_id]["value"]

    @property
    def entity_picture(self):
        """Return the entity picture url to display rainfall quantity"""
        rainfall_quantity = (
            0
            if self.native_value == 0
            else 0.2
            if self.native_value < 0.35
            else 0.5
            if self.native_value < 0.75
            else 1
            if self.native_value < 1.5
            else 2
            if self.native_value < 2.5
            else 3
            if self.native_value < 3.5
            else 4
            if self.native_value < 4.5
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


class NeaUVSensor(CoordinatorEntity, SensorEntity):
    """Implementation of a NEA UV sensor in Singapore."""

    _attr_has_entity_name = True
    _attr_translation_key = "uv_index"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:weather-sunny"

    def __init__(
        self,
        coordinator,
        config: MappingProxyType[str, Any],
        entry_id: str,
    ) -> None:
        """Initialise area sensor with a data instance and site."""
        super().__init__(coordinator)
        self.coordinator = coordinator
        self._platform = "sensor"
        self._prefix = config[CONF_SENSORS][CONF_PREFIX]
        self._entry_id = entry_id
        self._attr_device_info = main_device_info(entry_id)
        self.entity_id = (
            (self._platform + "." + self._prefix + "_uv")
            .lower()
            .replace(" ", "_")
        )

    @property
    def unique_id(self):
        """Return the unique ID."""
        return self._prefix + "_uv"

    @property
    def native_value(self):
        """Return the UV index."""
        return self.coordinator.data.uvindex.uv_index

    @property
    def extra_state_attributes(self) -> dict:
        """Return dict of additional properties to attach to sensors."""
        return {
            "Updated at": self.coordinator.data.uvindex.timestamp,
        }
