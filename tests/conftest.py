"""Configure pytest with Home Assistant module stubs."""
import sys
import os
from unittest.mock import MagicMock

# Ensure project root is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ---------------------------------------------------------------------------
# Stub base classes so HA entity classes can be inherited normally
# ---------------------------------------------------------------------------

class _CoordinatorEntity:
    def __init__(self, coordinator=None):
        self.coordinator = coordinator

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success


class _DataUpdateCoordinator:
    def __init__(self, *args, **kwargs):
        pass


class _SensorEntity:
    pass


class _WeatherEntity:
    pass


class _CameraEntity:
    pass


# ---------------------------------------------------------------------------
# homeassistant.components.weather
# ---------------------------------------------------------------------------
_ha_weather = MagicMock()
_ha_weather.ATTR_CONDITION_CLEAR_NIGHT = "clear-night"
_ha_weather.ATTR_CONDITION_CLOUDY = "cloudy"
_ha_weather.ATTR_CONDITION_FOG = "fog"
_ha_weather.ATTR_CONDITION_LIGHTNING = "lightning"
_ha_weather.ATTR_CONDITION_LIGHTNING_RAINY = "lightning-rainy"
_ha_weather.ATTR_CONDITION_PARTLYCLOUDY = "partlycloudy"
_ha_weather.ATTR_CONDITION_POURING = "pouring"
_ha_weather.ATTR_CONDITION_RAINY = "rainy"
_ha_weather.ATTR_CONDITION_SNOWY = "snowy"
_ha_weather.ATTR_CONDITION_SNOWY_RAINY = "snowy-rainy"
_ha_weather.ATTR_CONDITION_SUNNY = "sunny"
_ha_weather.ATTR_CONDITION_WINDY = "windy"
_ha_weather.ATTR_CONDITION_WINDY_VARIANT = "windy-variant"
_ha_weather.ATTR_FORECAST_CONDITION = "condition"
_ha_weather.ATTR_FORECAST_NATIVE_TEMP = "native_temperature"
_ha_weather.ATTR_FORECAST_NATIVE_TEMP_LOW = "native_templow"
_ha_weather.ATTR_FORECAST_NATIVE_WIND_SPEED = "native_wind_speed"
_ha_weather.ATTR_FORECAST_TIME = "datetime"
_ha_weather.ATTR_FORECAST_WIND_BEARING = "wind_bearing"
_ha_weather.WeatherEntity = _WeatherEntity
_ha_weather.WeatherEntityFeature = MagicMock()
_ha_weather.WeatherEntityFeature.FORECAST_DAILY = 1
_ha_weather.Forecast = dict

# ---------------------------------------------------------------------------
# homeassistant.components.sensor
# ---------------------------------------------------------------------------
_ha_sensor = MagicMock()
_ha_sensor.SensorDeviceClass = MagicMock()
_ha_sensor.SensorDeviceClass.PM25 = "pm25"
_ha_sensor.SensorDeviceClass.PRECIPITATION = "precipitation"
_ha_sensor.SensorEntity = _SensorEntity
_ha_sensor.SensorStateClass = MagicMock()
_ha_sensor.SensorStateClass.MEASUREMENT = "measurement"

# ---------------------------------------------------------------------------
# homeassistant.const
# ---------------------------------------------------------------------------
_ha_const = MagicMock()
_ha_const.CONF_NAME = "name"
_ha_const.CONF_SCAN_INTERVAL = "scan_interval"
_ha_const.CONF_SENSORS = "sensors"
_ha_const.CONF_TIMEOUT = "timeout"
_ha_const.CONF_REGION = "region"
_ha_const.CONF_PREFIX = "prefix"
_ha_const.CONF_SELECTOR = "selector"
_ha_const.UnitOfTemperature = MagicMock()
_ha_const.UnitOfTemperature.CELSIUS = "°C"
_ha_const.UnitOfLength = MagicMock()
_ha_const.UnitOfLength.MILLIMETERS = "mm"
_ha_const.UnitOfPressure = MagicMock()
_ha_const.UnitOfPressure.HPA = "hPa"
_ha_const.UnitOfSpeed = MagicMock()
_ha_const.UnitOfSpeed.KNOTS = "kn"
_ha_const.UnitOfPrecipitationDepth = MagicMock()
_ha_const.UnitOfPrecipitationDepth.MILLIMETERS = "mm"

# ---------------------------------------------------------------------------
# homeassistant.helpers.update_coordinator
# ---------------------------------------------------------------------------
_ha_coordinator = MagicMock()
_ha_coordinator.DataUpdateCoordinator = _DataUpdateCoordinator
_ha_coordinator.CoordinatorEntity = _CoordinatorEntity
_ha_coordinator.UpdateFailed = Exception

# ---------------------------------------------------------------------------
# homeassistant.components.camera
# ---------------------------------------------------------------------------
_ha_camera = MagicMock()
_ha_camera.Camera = _CameraEntity

# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# aiohttp stub — real exception hierarchy so except clauses work in tests
# ---------------------------------------------------------------------------

def _make_aiohttp_stub():
    stub = MagicMock()

    class ClientError(Exception):
        pass

    class ClientResponseError(ClientError):
        def __init__(self, request_info=None, history=None, *, status=None, **kwargs):
            super().__init__(status)
            self.status = status

    class ClientConnectionError(ClientError):
        pass

    class ClientTimeout:
        def __init__(self, **kwargs):
            pass

    stub.ClientError = ClientError
    stub.ClientResponseError = ClientResponseError
    stub.ClientConnectionError = ClientConnectionError
    stub.ClientTimeout = ClientTimeout
    stub.ClientSession = MagicMock()
    return stub


# ---------------------------------------------------------------------------
# Patch sys.modules before any source imports happen
# ---------------------------------------------------------------------------
sys.modules.update({
    "homeassistant": MagicMock(),
    "homeassistant.components": MagicMock(),
    "homeassistant.components.weather": _ha_weather,
    "homeassistant.components.sensor": _ha_sensor,
    "homeassistant.components.camera": _ha_camera,
    "homeassistant.config_entries": MagicMock(),
    "homeassistant.const": _ha_const,
    "homeassistant.core": MagicMock(),
    "homeassistant.helpers": MagicMock(),
    "homeassistant.helpers.aiohttp_client": MagicMock(),
    "homeassistant.helpers.httpx_client": MagicMock(),
    "homeassistant.helpers.update_coordinator": _ha_coordinator,
    "homeassistant.helpers.device_registry": MagicMock(),
    "homeassistant.helpers.entity_platform": MagicMock(),
    "homeassistant.helpers.config_validation": MagicMock(),
    "aiohttp": _make_aiohttp_stub(),
    "voluptuous": MagicMock(),
    "PIL": MagicMock(),
    "PIL.Image": MagicMock(),
    "PIL.ImageDraw": MagicMock(),
    "PIL.ImageFont": MagicMock(),
})
