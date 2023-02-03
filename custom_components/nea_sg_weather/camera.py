"""Support for retrieving weather data from NEA."""
from __future__ import annotations
from PIL import Image
import io
import asyncio
import logging
from types import MappingProxyType
from typing import Any
from datetime import datetime, timezone, timedelta
import math
import httpx

from homeassistant.components.camera import Camera
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME, CONF_PREFIX, CONF_SENSORS
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.httpx_client import get_async_client

from . import NeaWeatherDataUpdateCoordinator
from .const import (
    DOMAIN,
    RAIN_MAP_HEADERS,
    RAIN_MAP_URL_PREFIX,
    RAIN_MAP_URL_SUFFIX,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Add a weather camera entity from a config_entry."""
    coordinator: NeaWeatherDataUpdateCoordinator = hass.data[DOMAIN][
        config_entry.entry_id
    ]

    async_add_entities([NeaRainCamera(hass, coordinator, config_entry.data)])


class NeaRainCamera(Camera):
    """Implementation of a camera entity for rain map overlay."""

    def __init__(
        self,
        hass: HomeAssistant,
        coordinator,
        config: MappingProxyType[str, Any],
    ) -> None:
        """Initialise area sensor with a data instance and site."""
        super().__init__()
        self.hass = hass
        self.coordinator = coordinator
        self._name = config.get(CONF_NAME) + " Rain Map"
        self._limit_refetch = True
        self._supported_features = 0
        self.content_type = "image/png"
        self.verify_ssl = True
        self._last_query_time = None
        self._last_image_time = None
        self._last_image_time_pretty = None
        self._last_image = None
        self._images = []
        self._last_url = None
        self._platform = "camera"
        self._prefix = config[CONF_SENSORS][CONF_PREFIX]
        self.entity_id = (
            (self._platform + "." + self._prefix + "_rain_map")
            .lower()
            .replace(" ", "_")
        )
        self._last_state = None
        self._last_attributes = None
        self._updated_attributes = None

    @property
    def unique_id(self):
        """Return the unique ID."""
        return self._prefix + " Rain Map"

    @property
    def name(self):
        """Return the name of this device."""
        return self._name

    @property
    def supported_features(self):
        """Return supported features for this camera."""
        return self._supported_features

    def camera_image(
        self, width: int | None = None, height: int | None = None
    ) -> bytes | None:
        """Return bytes of camera image."""
        return asyncio.run_coroutine_threadsafe(
            self.async_camera_image(), self.hass.loop
        ).result()

    async def async_camera_image(
        self, width: int | None = None, height: int | None = None
    ) -> bytes | None:
        """Return a still image response from the camera."""

        async def get_image(current_image_time: int) -> bytes | None:
            url = RAIN_MAP_URL_PREFIX + str(current_image_time) + RAIN_MAP_URL_SUFFIX
            _LOGGER.debug("Getting rain map image from %s", url)
            try:
                async_client = get_async_client(self.hass, verify_ssl=self.verify_ssl)
                response = await async_client.get(url, headers=RAIN_MAP_HEADERS)
                response.raise_for_status()
                self._last_image = response.content
                self._last_image_time = current_image_time
                self._last_image_time_pretty = datetime.strptime(
                    str(current_image_time), "%Y%m%d%H%M"
                ).isoformat()
                self._last_url = url
                # Update timestamp from external coordinator entity
                self._last_state = self.hass.states.get(self.entity_id).state
                self._last_attributes = self.hass.states.get(self.entity_id).attributes
                self._updated_attributes = dict(self._last_attributes)
                self._updated_attributes["Updated at"] = self._last_image_time_pretty
                self._updated_attributes["URL"] = url
                self.hass.states.async_set(
                    self.entity_id, self._last_state, self._updated_attributes
                )
                _LOGGER.debug(
                    "Rain map image successfully updated at %s, new URL is %s",
                    datetime.strptime(
                        str(current_image_time), "%Y%m%d%H%M"
                    ).isoformat(),
                    url,
                )
                frame = Image.open(io.BytesIO(response.content))
                self._images.append(frame)
                # drop older frames when we have enough
                if len(self._images) > 12:
                    self._images = self._images[1:]
                # create animated gif of rain map
                if len(self._images) > 1:
                    _LOGGER.debug("Converting frames to gif")
                    buff = io.BytesIO()
                    self._images[0].save(buff, format='GIF', save_all=True, append_images=self._images[1:], optimize=False, duration=1000, disposal=2, loop=0)
                    self._last_image = buff.getvalue()
                return self._last_image

            except httpx.TimeoutException:
                _LOGGER.warning(
                    "Timeout getting camera image for %s from %s", self._name, url
                )
                return self._last_image

            except (httpx.HTTPStatusError, httpx.RequestError) as err:
                if response.status_code == 404:
                    # Image not ready, check older image urls
                    _LOGGER.debug(
                        "%s rain map image not ready, trying previous images",
                        current_image_time,
                    )

                    # minor fix for whole hours
                    if str(current_image_time)[-2:] == "00":
                        _skip_minutes = 45
                    else:
                        _skip_minutes = 5

                    if current_image_time - _skip_minutes == self._last_image_time:
                        return self._last_image
                    else:
                        return await get_image(current_image_time - _skip_minutes)
                else:
                    _LOGGER.warning(
                        "Error getting new camera image for %s from %s: %s",
                        self._name,
                        url,
                        err,
                    )
                    return self._last_image

        _current_query_time = int(
            datetime.strftime(datetime.now(timezone(timedelta(hours=8))), "%Y%m%d%H%M")
        )

        if _current_query_time != self._last_query_time:
            self._last_query_time = _current_query_time
            _current_image_time = math.floor(_current_query_time / 5) * 5
            if _current_image_time != self._last_image_time:
                return await get_image(_current_image_time)

        return self._last_image

    async def stream_source(self):
        """Return the source of the stream."""
        return None

    @property
    def extra_state_attributes(self) -> dict:
        """Return dict of additional properties to attach to sensors."""
        return {
            "Updated at": self._last_image_time_pretty,
            "URL": self._last_url,
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
