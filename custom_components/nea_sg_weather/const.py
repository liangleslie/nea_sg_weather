"""New config variable"""
from homeassistant.components.weather import (
    ATTR_CONDITION_CLEAR_NIGHT,
    ATTR_CONDITION_CLOUDY,
    ATTR_CONDITION_FOG,
    ATTR_CONDITION_LIGHTNING,
    ATTR_CONDITION_LIGHTNING_RAINY,
    ATTR_CONDITION_PARTLYCLOUDY,
    ATTR_CONDITION_POURING,
    ATTR_CONDITION_RAINY,
    ATTR_CONDITION_SNOWY,
    ATTR_CONDITION_SNOWY_RAINY,
    ATTR_CONDITION_SUNNY,
    ATTR_CONDITION_WINDY,
    ATTR_CONDITION_WINDY_VARIANT,
)
from homeassistant.const import CONF_REGION

CONF_AREAS = "areas"
CONF_RAIN = "rain"
CONF_SENSOR = "sensor"
CONF_WEATHER = "weather"

DOMAIN = "nea_sg_weather"
ATTRIBUTION = "Weather data from Singapore's NEA"
DEFAULT_NAME = "Singapore Weather"
DEFAULT_SCAN_INTERVAL = 15
DEFAULT_TIMEOUT = 10
HEADERS = {
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.45 Safari/537.36",
}
RAIN_MAP_HEADERS = {
    "authority": "www.weather.gov.sg",
    "referer": "https://www.nea.gov.sg/weather/rain-areas",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.45 Safari/537.36",
}
RAIN_MAP_URL_PREFIX = "https://www.weather.gov.sg/files/rainarea/50km/v2/dpsri_70km_"
RAIN_MAP_URL_SUFFIX = "0000dBR.dpsri.png"

FORECAST_ICON_BASE_URL = "https://www.nea.gov.sg/assets/images/icons/weather-bg/"

MAP_CONDITION = {
    "Mist": ATTR_CONDITION_FOG,
    "Cloudy": ATTR_CONDITION_CLOUDY,
    "Drizzle": ATTR_CONDITION_RAINY,
    "Fair": ATTR_CONDITION_SUNNY,
    "Fair (Day)": ATTR_CONDITION_SUNNY,
    "Fog": ATTR_CONDITION_FOG,
    "Fair (Night)": ATTR_CONDITION_CLEAR_NIGHT,
    "Fair & Warm": ATTR_CONDITION_SUNNY,
    "Heavy Thundery Showers with Gusty Winds": ATTR_CONDITION_LIGHTNING,
    "Heavy Rain": ATTR_CONDITION_POURING,
    "Heavy Showers": ATTR_CONDITION_POURING,
    "Heavy Thundery Showers": ATTR_CONDITION_LIGHTNING,
    "Hazy": ATTR_CONDITION_FOG,
    "Slightly Hazy": ATTR_CONDITION_FOG,
    "Light Rain": ATTR_CONDITION_RAINY,
    "Light Showers": ATTR_CONDITION_RAINY,
    "Overcast": ATTR_CONDITION_CLOUDY,
    "Partly Cloudy": ATTR_CONDITION_PARTLYCLOUDY,
    "Partly Cloudy (Day)": ATTR_CONDITION_PARTLYCLOUDY,
    "Partly Cloudy (Night)": ATTR_CONDITION_PARTLYCLOUDY,
    "Passing Showers": ATTR_CONDITION_RAINY,
    "Moderate Rain": ATTR_CONDITION_RAINY,
    "Showers": ATTR_CONDITION_RAINY,
    "Strong Winds, Showers": ATTR_CONDITION_POURING,
    "Snow": ATTR_CONDITION_SNOWY,
    "Strong Winds, Rain": ATTR_CONDITION_RAINY,
    "Snow Showers": ATTR_CONDITION_SNOWY_RAINY,
    "Sunny": ATTR_CONDITION_SUNNY,
    "Strong Winds": ATTR_CONDITION_WINDY,
    "Thundery Showers": ATTR_CONDITION_LIGHTNING_RAINY,
    "Windy, Cloudy": ATTR_CONDITION_WINDY_VARIANT,
    "Windy": ATTR_CONDITION_WINDY,
    "Windy, Fair": ATTR_CONDITION_WINDY,
    "Windy, Rain": ATTR_CONDITION_RAINY,
    "Windy, Showers": ATTR_CONDITION_RAINY,
}

FORECAST_ICON_MAP_CONDITION = {
    "Mist": "BR",
    "Cloudy": "CL",
    "Drizzle": "DR",
    "Fair": "FA",
    "Fair (Day)": "FA",
    "Fog": "FG",
    "Fair (Night)": "FN",
    "Fair & Warm": "FW",
    "Heavy Thundery Showers with Gusty Winds": "HG",
    "Heavy Rain": "HR",
    "Heavy Showers": "HS",
    "Heavy Thundery Showers": "HT",
    "Hazy": "HZ",
    "Slightly Hazy": "LH",
    "Light Rain": "LR",
    "Light Showers": "LS",
    "Overcast": "OC",
    "Partly Cloudy": "PC",
    "Partly Cloudy (Day)": "PC",
    "Partly Cloudy (Night)": "PN",
    "Passing Showers": "PS",
    "Moderate Rain": "RA",
    "Showers": "SH",
    "Strong Winds, Showers": "SK",
    "Snow": "SN",
    "Strong Winds, Rain": "SR",
    "Snow Showers": "SS",
    "Sunny": "SU",
    "Strong Winds": "SW",
    "Thundery Showers": "TL",
    "Windy, Cloudy": "WC",
    "Windy": "WD",
    "Windy, Fair": "WF",
    "Windy, Rain": "WR",
    "Windy, Showers": "WS",
}

FORECAST_MAP_CONDITION = {
    "thundery showers": ATTR_CONDITION_LIGHTNING_RAINY,
    "partly cloudy": ATTR_CONDITION_PARTLYCLOUDY,
    "rain": ATTR_CONDITION_RAINY,
    "showers": ATTR_CONDITION_RAINY,
    "fair": ATTR_CONDITION_SUNNY,
    "hazy": ATTR_CONDITION_FOG,
    "cloudy": ATTR_CONDITION_CLOUDY,
    "overcast": ATTR_CONDITION_CLOUDY,
    "windy": ATTR_CONDITION_WINDY,
}

AREAS = [
    "Ang Mo Kio",
    "Bedok",
    "Bishan",
    "Boon Lay",
    "Bukit Batok",
    "Bukit Merah",
    "Bukit Panjang",
    "Bukit Timah",
    "Central Water Catchment",
    "Changi",
    "Choa Chu Kang",
    "Clementi",
    "City",
    "Geylang",
    "Hougang",
    "Jalan Bahar",
    "Jurong East",
    "Jurong Island",
    "Jurong West",
    "Kallang",
    "Lim Chu Kang",
    "Mandai",
    "Marine Parade",
    "Novena",
    "Pasir Ris",
    "Paya Lebar",
    "Pioneer",
    "Pulau Tekong",
    "Pulau Ubin",
    "Punggol",
    "Queenstown",
    "Seletar",
    "Sembawang",
    "Sengkang",
    "Sentosa",
    "Serangoon",
    "Southern Islands",
    "Sungei Kadut",
    "Tampines",
    "Tanglin",
    "Tengah",
    "Toa Payoh",
    "Tuas",
    "Western Islands",
    "Western Water Catchment",
    "Woodlands",
    "Yishun",
]

REGIONS = ["West", "East", "Central", "South", "North"]

WEATHER_ENDPOINTS = {
    "forecast2hr": "https://api.data.gov.sg/v1/environment/2-hour-weather-forecast",
    "temperature": "https://api.data.gov.sg/v1/environment/air-temperature",
    "humidity": "https://api.data.gov.sg/v1/environment/relative-humidity",
    "wind-direction": "https://api.data.gov.sg/v1/environment/wind-direction",
    "wind-speed": "https://api.data.gov.sg/v1/environment/wind-speed",
    "forecast4day": "https://api.data.gov.sg/v1/environment/4-day-weather-forecast",
}

SECONDARY_WEATHER_ENDPOINTS = {
    "forecast2hr": "https://www.nea.gov.sg/api/WeatherForecast/forecast24hrnowcast2hrs",
    "temperature": "",
    "humidity": "",
    "wind-direction": "",
    "wind-speed": "",
    "forecast4day": "https://www.nea.gov.sg/api/Weather4DayOutlook/GetData",
}

AREAS_ENDPOINTS = {
    "forecast2hr": "https://api.data.gov.sg/v1/environment/2-hour-weather-forecast"
}

SECONDARY_AREAS_ENDPOINTS = {
    "forecast2hr": "https://www.nea.gov.sg/api/WeatherForecast/forecast24hrnowcast2hrs"
}

REGION_ENDPOINTS = {
    "forecast24hr": "https://api.data.gov.sg/v1/environment/24-hour-weather-forecast"
}

SECONDARY_REGION_ENDPOINTS = {"forecast24hr": ""}

RAIN_ENDPOINTS = {}

ENDPOINTS = {
    CONF_WEATHER: WEATHER_ENDPOINTS,
    CONF_AREAS: AREAS_ENDPOINTS,
    CONF_REGION: REGION_ENDPOINTS,
    CONF_RAIN: RAIN_ENDPOINTS,
}

SECONDARY_ENDPOINTS = {
    CONF_WEATHER: SECONDARY_WEATHER_ENDPOINTS,
    CONF_AREAS: SECONDARY_AREAS_ENDPOINTS,
    CONF_REGION: SECONDARY_REGION_ENDPOINTS,
    CONF_RAIN: RAIN_ENDPOINTS,
}
