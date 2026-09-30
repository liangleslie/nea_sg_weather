"""Config flow to configure NEA SG Weather component."""
from __future__ import annotations

import logging

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.const import (
    CONF_NAME,
    CONF_PREFIX,
    CONF_REGION,
    CONF_SCAN_INTERVAL,
    CONF_SELECTOR,
    CONF_SENSORS,
    CONF_TIMEOUT,
)
from homeassistant.core import callback
import homeassistant.helpers.config_validation as cv

from .const import (
    AREAS,
    CONF_AREAS,
    CONF_RAIN,
    CONF_SENSOR,
    CONF_WEATHER,
    DEFAULT_NAME,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_TIMEOUT,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


@callback
def configured_instances(hass):
    """Return a set of configured NEA SG Weather instances."""
    entries = []
    for entry in hass.config_entries.async_entries(DOMAIN):
        entries.append(f"{entry.data.get(CONF_NAME)}")
    return set(entries)


class NeaWeatherFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for NEA SG Weather component."""

    VERSION = 1

    def __init__(self):
        """Init NeaWeatherFlowHandler."""
        self._errors = {}
        self._data = {}

    async def async_step_user(self, user_input=None):
        """Handle a flow initialized by the user."""
        self._errors = {}

        if user_input is not None:
            if user_input[CONF_NAME] not in configured_instances(self.hass):
                if user_input[CONF_SENSOR] or user_input[CONF_WEATHER]:
                    if user_input[CONF_SENSOR]:
                        # Additional config flow if sensors need to be set up
                        self._data = user_input
                        self._data[CONF_SENSORS] = {
                            CONF_PREFIX: '',
                            CONF_REGION: bool(),
                            CONF_RAIN: bool(),
                            CONF_AREAS: list(),
                        }
                        return await self.async_step_sensor()
                    elif user_input[CONF_WEATHER]:
                        return self.async_create_entry(
                            title=user_input[CONF_NAME], data=user_input
                        )
                else:
                    self._errors[CONF_NAME] = "no_entities_selected"
            else:
                self._errors[CONF_NAME] = "already_configured"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Optional(CONF_NAME, default=DEFAULT_NAME): str,
                    vol.Optional(CONF_WEATHER, default=True): cv.boolean,
                    vol.Optional(CONF_SENSOR, default=False): cv.boolean,
                    vol.Optional(
                        CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL
                    ): cv.positive_int,
                    vol.Optional(
                        CONF_TIMEOUT, default=DEFAULT_TIMEOUT
                    ): cv.positive_int,
                }
            ),
            errors=self._errors,
        )

    async def async_step_sensor(self, user_input=None):
        """Second step in config flow for additional sensor settings."""
        self._errors = {}
        if user_input is not None:
            self._data[CONF_SENSORS][CONF_PREFIX] = user_input[CONF_PREFIX]
            self._data[CONF_SENSORS][CONF_REGION] = user_input[CONF_REGION]
            self._data[CONF_SENSORS][CONF_RAIN] = user_input[CONF_RAIN]
            self._data[CONF_SENSORS][CONF_AREAS] = user_input[CONF_AREAS]
            return self.async_create_entry(title=self._data[CONF_NAME], data=self._data)

        return self.async_show_form(
            step_id="sensor",
            data_schema=vol.Schema(
                {
                    vol.Optional(CONF_PREFIX, default=DEFAULT_NAME): str,
                    vol.Optional(CONF_AREAS, default=["All"]): cv.multi_select(
                        dict(zip(["All"] + AREAS, ["All"] + AREAS))
                    ),
                    vol.Optional(CONF_REGION, default=False): cv.boolean,
                    vol.Optional(CONF_RAIN, default=False): cv.boolean,
                }
            ),
            errors=self._errors,
        )

    async def async_step_reconfigure(
        self, user_input: dict | None = None
    ) -> ConfigFlowResult:
        """Change which entities an existing entry sets up.

        The entry name and sensor prefix are kept as they are: entity IDs are
        built from them, so changing either would replace every entity.
        Entities switched off here are removed when the entry reloads (see
        async_setup_entry in __init__.py and sensor.py).
        """
        self._errors = {}
        entry = self._get_reconfigure_entry()
        current = entry.data
        sensors = current.get(CONF_SENSORS, {})

        if user_input is not None:
            if user_input[CONF_WEATHER] or user_input[CONF_SENSOR]:
                return self.async_update_reload_and_abort(
                    entry,
                    data_updates={
                        CONF_WEATHER: user_input[CONF_WEATHER],
                        CONF_SENSOR: user_input[CONF_SENSOR],
                        CONF_SCAN_INTERVAL: user_input[CONF_SCAN_INTERVAL],
                        CONF_TIMEOUT: user_input[CONF_TIMEOUT],
                        CONF_SENSORS: {
                            # A weather-only entry has no prefix yet; use the
                            # entry name, as entity IDs elsewhere derive from it.
                            CONF_PREFIX: sensors.get(CONF_PREFIX, current[CONF_NAME]),
                            CONF_AREAS: user_input[CONF_AREAS],
                            CONF_REGION: user_input[CONF_REGION],
                            CONF_RAIN: user_input[CONF_RAIN],
                        },
                    },
                )
            self._errors["base"] = "no_entities_selected"

        area_options = ["All"] + AREAS
        current_areas = [
            area for area in sensors.get(CONF_AREAS, ["All"]) if area in area_options
        ]
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_WEATHER, default=current.get(CONF_WEATHER, True)
                    ): cv.boolean,
                    vol.Optional(
                        CONF_SENSOR, default=current.get(CONF_SENSOR, False)
                    ): cv.boolean,
                    vol.Optional(
                        CONF_AREAS, default=current_areas
                    ): cv.multi_select(dict(zip(area_options, area_options))),
                    vol.Optional(
                        CONF_REGION, default=sensors.get(CONF_REGION, False)
                    ): cv.boolean,
                    vol.Optional(
                        CONF_RAIN, default=sensors.get(CONF_RAIN, False)
                    ): cv.boolean,
                    vol.Optional(
                        CONF_SCAN_INTERVAL,
                        default=current.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
                    ): cv.positive_int,
                    vol.Optional(
                        CONF_TIMEOUT, default=current.get(CONF_TIMEOUT, DEFAULT_TIMEOUT)
                    ): cv.positive_int,
                }
            ),
            errors=self._errors,
        )

    async def async_step_import(self, user_input: dict | None = None) -> ConfigFlowResult:
        """Handle configuration by yaml file."""
        return await self.async_step_user(user_input)

    async def async_step_onboarding(self, data=None):
        """Handle a flow initialized by onboarding."""
        return self.async_create_entry(
            title=DEFAULT_NAME,
            data={
                CONF_NAME: DEFAULT_NAME,
                CONF_SELECTOR: "WEATHER",
                CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL,
                CONF_TIMEOUT: DEFAULT_TIMEOUT,
            },
        )
