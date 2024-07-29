"""
Wrapper/scraper to easily access SG weather data from `www.nea.gov.sg` and `www.weather.gov.sg`

Weather().api.json --> simulated json output in the same format as data.gov.sg. Dict keys map to endpoint pathinfo, i.e. simulated json output of `https://api.data.gov.sg/v1/environment/24-hour-weather-forecast` can be returned with weather.api.json['24-hour-weather-forecast']

Weather().current
Weather().area
Weather().region
Weather().week
Weather().stations


usage:
```
from weathersg import Weather

weather = Weather()
simulated_resp = weather.api.json['24-hour-weather-forecast']
```

"""

from __future__ import annotations
import requests
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from dateutil import parser
import math
import logging


CODE_CONDITION_MAP = {
    "BR": "fog",
    "CL": "cloudy",
    "DR": "drizzle",
    "FA": "sunny",
    "FG": "fog",
    "FN": "clear-night",
    "FW": "sunny",
    "HG": "lightning",
    "HR": "pouring",
    "HS": "pouring",
    "HT": "lightning",
    "HZ": "fog",
    "LH": "fog",
    "LR": "drizzle",
    "LS": "rainy",
    "OC": "cloudy",
    "PC": "partlycloudy",
    "PN": "partlycloudy-night",
    "PS": "rainy",
    "RA": "rainy",
    "SH": "rainy",
    "SK": "pouring",
    "SN": "snowy",
    "SR": "rain-wind",
    "SS": "snowy-rainy",
    "SU": "sunny",
    "SW": "windy",
    "TL": "lightning-rainy",
    "WC": "windy-variant",
    "WD": "windy",
    "WF": "windy",
    "WR": "rain-wind",
    "WS": "rain-wind",
}

CODE_DESCRIPTION_MAP = {
    "BR": "Mist",
    "CL": "Cloudy",
    "DR": "Drizzle",
    "FA": "Fair (Day)",
    "FG": "Fog",
    "FN": "Fair (Night)",
    "FW": "Fair & Warm",
    "HG": "Heavy Thundery Showers with Gusty Winds",
    "HR": "Heavy Rain",
    "HS": "Heavy Showers",
    "HT": "Heavy Thundery Showers",
    "HZ": "Hazy",
    "LH": "Slightly Hazy",
    "LR": "Light Rain",
    "LS": "Light Showers",
    "OC": "Overcast",
    "PC": "Partly Cloudy (Day)",
    "PN": "Partly Cloudy (Night)",
    "PS": "Passing Showers",
    "RA": "Moderate Rain",
    "SH": "Showers",
    "SK": "Strong Winds, Showers",
    "SN": "Snow",
    "SR": "Strong Winds, Rain",
    "SS": "Snow Showers",
    "SU": "Sunny",
    "SW": "Strong Winds",
    "TL": "Thundery Showers",
    "WC": "Windy, Cloudy",
    "WD": "Windy",
    "WF": "Windy, Fair",
    "WR": "Windy, Rain",
    "WS": "Windy, Showers",
}

NEA_HEADERS = {"referer": "https://www.nea.gov.sg/"}

WEATHERSG_HEADERS = {
    "authority": "www.weather.gov.sg",
    "referer": "www.weather.gov.sg",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.45 Safari/537.36",
}

GET_ENDPOINTS = {
    "4day": "https://www.nea.gov.sg/api/Weather4DayOutlook/GetData/",
    "24hr": "https://www.nea.gov.sg/api/WeatherForecast/forecast24hrnowcast2hrs/",
    "current": "https://www.nea.gov.sg/api/Weather24hrs/GetData/",
    "temperature": "https://www.weather.gov.sg/weather-currentobservations-temperature/",
    "humidity": "https://www.weather.gov.sg/weather-currentobservations-relative-humidity/",
    "wind": "https://www.weather.gov.sg/weather-currentobservations-wind/",
    "rainfall": "https://www.weather.gov.sg/weather-currentobservations-rainfall/",
}

POST_ENDPOINTS = {
    "temperature": "https://www.weather.gov.sg/wp-content/themes/wiptheme/page-functions/functions-ajax-temperature-chart.php",
    "humidity": "https://www.weather.gov.sg/wp-content/themes/wiptheme/page-functions/functions-ajax-relative-humidity-chart.php",
    "wind": "https://www.weather.gov.sg/wp-content/themes/wiptheme/page-functions/functions-ajax-wind-chart.php",
    "rainfall": "https://www.weather.gov.sg/wp-content/themes/wiptheme/page-functions/functions-weather-current-observations-rainfall-ajax.php",
}

REALTIME_WEATHER_CONST = {
    "temperature": {"reading_type": "DBT 1M F", "reading_unit": "deg C"},
    "humidity": {"reading_type": "RH 1M F", "reading_unit": "percentage"},
    "rainfall": {"reading_type": "TB1 Rainfall 5 Minute Total F", "reading_unit": "mm"},
    "wind-direction": {
        "reading_type": "Converted from NSEW symbols at 45 deg intervals",
        "reading_unit": "degrees",
    },
    "wind": {"reading_type": "Wind Speed AVG(S)10M M1M", "reading_unit": "knots"},
}

WIND_DIR_TO_DEG_MAP = {
    "N": 0,
    "NE": 45,
    "E": 90,
    "SE": 135,
    "S": 180,
    "SW": 225,
    "W": 270,
    "NW": 315,
    "": math.nan,
}

_LOGGER = logging.getLogger(__name__)


class Weather:
    """
    Main class to easily access weather objects
    """

    def __init__(self) -> None:
        self.data = self.WeatherData()
        self.stations = self.Stations(self.data)
        self.current = self.Current(self.data)
        self.area = self.Area(self.data)
        self.region = self.Region(self.data)
        self.week = self.Week(self.data)
        self.api = self.API(self)

    class WeatherData:
        """
        Class to hold raw responses from endpoints
        """

        def __init__(self) -> None:
            # get data from NEA API
            self.raw_resp = {}
            for k, v in GET_ENDPOINTS.items():
                _LOGGER.debug(f"Getting {k}: {v}")
                _latest_timestamp = (
                    str(int(str(round(datetime.now().timestamp()))[:-2]) // 3 * 3)
                    + "00"
                )  # API endpoint only accepts time rounded to nearest 5min
                _LOGGER.debug(f"Latest Timestamp {k}: {_latest_timestamp}")
                self.raw_resp[k] = {}
                if GET_ENDPOINTS[k][:23] == "https://www.nea.gov.sg/":
                    self.raw_resp[k]["raw"] = requests.get(
                        GET_ENDPOINTS[k] + _latest_timestamp, headers=NEA_HEADERS
                    )
                    self.raw_resp[k]["processed"] = self.raw_resp[k]["raw"].json()
                    # print(k + ": json stored")
                else:  # scrape data from weather.sg
                    self.raw_resp[k]["raw"] = requests.get(
                        GET_ENDPOINTS[k], headers=WEATHERSG_HEADERS
                    )
                    self.raw_resp[k]["processed"] = {}
                    soup = BeautifulSoup(self.raw_resp[k]["raw"].content, "html.parser")
                    self.raw_resp[k]["obs_datetime"] = soup.find(class_="date-obs").text

                    # attempt to get station metadata and latlon
                    if (
                        k == "humidity"
                    ):  # workaround for humidity page which uses different variable name
                        raw_stations_metadata = self.raw_resp[k]["raw"].text.split(
                            '{stationCode:"'
                        )[1:]

                    else:
                        raw_stations_metadata = self.raw_resp[k]["raw"].text.split(
                            '{station_code:"'
                        )[1:]

                    stations_metadata = {}
                    for raw_station_metadata in raw_stations_metadata:
                        station_metadata = raw_station_metadata.split('"')[:5]
                        stations_metadata[station_metadata[0]] = {
                            "lat": station_metadata[2],
                            "lon": station_metadata[4],
                        }

                    # rainfall data needs to be requested for by POSTing to a separate endpoint
                    if k == "rainfall":
                        self.raw_resp[k]["raw"] = requests.post(
                            POST_ENDPOINTS[k], data={"tableName": "30", "type": "html"}
                        )
                        soup = BeautifulSoup(
                            self.raw_resp[k]["raw"].content, "html.parser"
                        )

                    # process readings
                    stations_reading = soup.find_all(class_="sgr")
                    for station_reading in stations_reading:
                        self.raw_resp[k]["processed"][station_reading["id"]] = {}
                        self.raw_resp[k]["processed"][station_reading["id"]]["id"] = (
                            station_reading["id"]
                        )
                        self.raw_resp[k]["processed"][station_reading["id"]][
                            "station_name"
                        ] = BeautifulSoup(
                            station_reading["data-bs-content"], "html.parser"
                        ).strong.text
                        self.raw_resp[k]["processed"][station_reading["id"]][
                            "value"
                        ] = station_reading.text
                        self.raw_resp[k]["processed"][station_reading["id"]]["lat"] = (
                            stations_metadata[station_reading["id"]]["lat"]
                        )
                        self.raw_resp[k]["processed"][station_reading["id"]]["lon"] = (
                            stations_metadata[station_reading["id"]]["lon"]
                        )

                        if k == "wind":
                            self.raw_resp[k]["processed"][station_reading["id"]][
                                "direction"
                            ] = station_reading.img["alt"]
                _LOGGER.debug(f"{k}: {self.raw_resp[k]}")
                _LOGGER.debug(f"{k}: processed html with BeautifulSoup")

    class Current:
        """
        Current weather
        """

        def __init__(self, data: Weather.WeatherData) -> None:
            self.data = data.raw_resp["current"]["processed"]
            self.obs_datetime = parser.parse(
                self.data["forecast_issue"].replace("Updated at ", "")
            ).strftime("%Y-%m-%dT%H:%M:%S+08:00")
            self.temperature_high = self.data["temperature_high"]
            self.temperature_low = self.data["temperature_low"]
            self.humidity_high = self.data["relative_humidity_high"]
            self.humidity_low = self.data["relative_humidity_low"]
            self.icon = self.data["weather_icon"]
            self.code = self.data["weather_code"]
            self.condition = CODE_CONDITION_MAP[self.code]
            self.description = self.data["weather_desc"]
            temp_list = [
                float(station["value"])
                for station in data.raw_resp["temperature"]["processed"].values()
            ]
            self.temperature = sum(temp_list) / len(temp_list)
            humd_list = [
                float(station["value"])
                for station in data.raw_resp["humidity"]["processed"].values()
            ]
            self.humidity = sum(humd_list) / len(humd_list)
            self.wind_speed = self.data["wind_speed"]
            self.wind_direction = self.data["wind_direction"]
            self.json = self.__dict__.copy()
            self.json.pop("data")

    class Area:
        """
        Subclass for area forecast
        """

        def __init__(self, data: Weather.WeatherData) -> None:
            data = data.raw_resp["24hr"]["processed"]["Channel2HrForecast"]
            self.obs_date = data["Item"]["ForecastIssue"]["Date"]
            self.obs_time = data["Item"]["ForecastIssue"]["Time"]
            self.obs_datetime = data["Item"]["ForecastIssue"]["DateTimeStr"]
            self.areas = [
                a["LocationName"] for a in data["Item"]["WeatherForecast"]["Area"]
            ]
            self.all = []
            for i in range(len(self.areas)):
                area_weather = data["Item"]["WeatherForecast"]["Area"][i]
                self.all.append(
                    {
                        "Name": area_weather["Name"],
                        "Lat": area_weather["Lat"],
                        "Lon": area_weather["Lon"],
                        "Code": area_weather["Forecast"],
                        "Condition": CODE_CONDITION_MAP[area_weather["Forecast"]],
                    }
                )
                self.__dict__[area_weather["LocationName"]] = self.all[i]

    class Region:
        """
        Subclass for region forecast
        """

        def __init__(self, data: Weather.WeatherData) -> None:
            data = data.raw_resp["24hr"]["processed"]["Channel24HrForecast"]
            self.obs_date = data["Main"]["ForecastIssue"]["Date"]
            self.obs_time = data["Main"]["ForecastIssue"]["Time"]
            self.obs_datetime = data["Main"]["ForecastIssue"]["DateTimeStr"]
            regions = ["north", "south", "east", "west", "central"]
            self.all = {}
            for region in regions:
                self.__dict__[region] = []
                for i in range(len(data["Forecasts"])):
                    self.__dict__[region].append(
                        {
                            "Region": region,
                            "Type": data["Forecasts"][i]["Type"],
                            "TimePeriod": data["Forecasts"][i]["TimePeriod"],
                            "Code": data["Forecasts"][i]["Wx" + region],
                            "Condition": CODE_CONDITION_MAP[
                                data["Forecasts"][i]["Wx" + region]
                            ],
                        }
                    )
                    self.all[region] = self.__dict__[region]

    class Week:
        """
        Next 4 day weather
        """

        def __init__(self, data: Weather.WeatherData) -> None:
            self.data = data.raw_resp["4day"]["processed"]

    class Stations:
        """
        Measurements by station ID
        """

        def __init__(self, data: Weather.WeatherData) -> None:
            self.list = set()
            for i in ["temperature", "humidity", "wind", "rainfall"]:
                self.list = self.list.union(set(data.raw_resp[i]["processed"].keys()))
            for station in self.list:
                self.__dict__[station] = {
                    "rainfall": {},
                    "temperature": {},
                    "humidity": {},
                    "wind": {},
                }
                # match station id to name
                if station in data.raw_resp["rainfall"]["processed"].keys():
                    self.__dict__[station]["name"] = data.raw_resp["rainfall"][
                        "processed"
                    ][station]["station_name"]
                    self.__dict__[station]["lat"] = data.raw_resp["rainfall"][
                        "processed"
                    ][station]["lat"]
                    self.__dict__[station]["lon"] = data.raw_resp["rainfall"][
                        "processed"
                    ][station]["lon"]
                    self.__dict__[station]["rainfall"] = {
                        "value": data.raw_resp["rainfall"]["processed"][station][
                            "value"
                        ],
                        "unit": "mm",
                        "obs_datetime": data.raw_resp["rainfall"]["obs_datetime"],
                    }
                if station in data.raw_resp["temperature"]["processed"].keys():
                    self.__dict__[station]["name"] = data.raw_resp["temperature"][
                        "processed"
                    ][station]["station_name"]
                    self.__dict__[station]["lat"] = data.raw_resp["temperature"][
                        "processed"
                    ][station]["lat"]
                    self.__dict__[station]["lon"] = data.raw_resp["temperature"][
                        "processed"
                    ][station]["lon"]
                    self.__dict__[station]["temperature"] = {
                        "value": data.raw_resp["temperature"]["processed"][station][
                            "value"
                        ],
                        "unit": "°C",
                        "obs_datetime": data.raw_resp["temperature"]["obs_datetime"],
                    }
                if station in data.raw_resp["humidity"]["processed"].keys():
                    self.__dict__[station]["name"] = data.raw_resp["humidity"][
                        "processed"
                    ][station]["station_name"]
                    self.__dict__[station]["lat"] = data.raw_resp["humidity"][
                        "processed"
                    ][station]["lat"]
                    self.__dict__[station]["lon"] = data.raw_resp["humidity"][
                        "processed"
                    ][station]["lon"]
                    self.__dict__[station]["humidity"] = {
                        "value": data.raw_resp["humidity"]["processed"][station][
                            "value"
                        ],
                        "unit": "%",
                        "obs_datetime": data.raw_resp["humidity"]["obs_datetime"],
                    }
                if station in data.raw_resp["wind"]["processed"].keys():
                    self.__dict__[station]["name"] = data.raw_resp["wind"]["processed"][
                        station
                    ]["station_name"]
                    self.__dict__[station]["lat"] = data.raw_resp["wind"]["processed"][
                        station
                    ]["lat"]
                    self.__dict__[station]["lon"] = data.raw_resp["wind"]["processed"][
                        station
                    ]["lon"]
                    self.__dict__[station]["wind"] = {
                        "value": data.raw_resp["wind"]["processed"][station]["value"],
                        "direction": data.raw_resp["wind"]["processed"][station][
                            "direction"
                        ],
                        "unit": "km/h",
                        "obs_datetime": data.raw_resp["wind"]["obs_datetime"],
                    }

        def get_detailed_station_temperature(self, hr_type="6") -> dict():
            """
            Get detailed temperature data
            """
            return

        def get_detailed_station_humidity(self, hr_type="6") -> dict():
            """
            Get detailed humidity data
            """
            return

        def get_detailed_station_rainfall(self, hr_type="6") -> dict():
            """
            Get detailed rainfall data
            """
            return

        def get_detailed_station_wind(self, hr_type="6") -> dict():
            """
            Get detailed wind data
            """
            return

    class API:
        """
        Simulated data.gov.sg responses
        """

        def __init__(self, weather: Weather) -> None:
            self.__weather = weather
            self.json = {
                "2-hour-weather-forecast": self.gen_2_hour_weather_forecast(),
                "24-hour-weather-forecast": self.gen_24_hour_weather_forecast(),
                "4-day-weather-forecast": self.gen_4_day_weather_forecast(),
                "air-temperature": self.gen_realtime_weather("temperature"),
                "rainfall": self.gen_realtime_weather("rainfall"),
                "relative-humidity": self.gen_realtime_weather("humidity"),
                "wind-direction": self.gen_realtime_weather("wind-direction"),
                "wind-speed": self.gen_realtime_weather("wind"),
            }

        def gen_2_hour_weather_forecast(self) -> dict:
            """
            Simulate response for _2-hour-weather-forecast_ endpoint
            """

            data_2_hour_weather_forecast = self.__weather.data.raw_resp["24hr"][
                "processed"
            ]["Channel2HrForecast"]
            update_datetime_2_hour = parser.parse(
                data_2_hour_weather_forecast["Item"]["ForecastIssue"]["DateTimeStr"]
            ).strftime("%Y-%m-%dT%H:%M:%S+08:00")

            # replace midnight/midnight with time that can be parsed by parser
            valid_timestr_2_hour = (
                data_2_hour_weather_forecast["Item"]["ValidTime"]
                .replace("Midnight", "12.00 am")
                .replace("Midday", "12.00 pm")
                .split(" to ")
            )
            output = {
                "api_info": {"status": "healthy"},
                "area_metadata": [],
                "items": [
                    {
                        "update_timestamp": update_datetime_2_hour,
                        "timestamp": update_datetime_2_hour,
                        "valid_period": {
                            "start": parser.parse(valid_timestr_2_hour[0]).strftime(
                                "%Y-%m-%dT%H:%M:%S+08:00"
                            ),
                            "end": parser.parse(valid_timestr_2_hour[1]).strftime(
                                "%Y-%m-%dT%H:%M:%S+08:00"
                            ),
                        },
                        "forecasts": [],
                    }
                ],
            }

            i = 0
            for area in self.__weather.area.all:
                output["area_metadata"].append(
                    {
                        "name": area["Name"],
                        "label_location": {
                            "latitude": area["Lat"],
                            "longitude": area["Lon"],
                        },
                    }
                )
                output["items"][0]["forecasts"].append(
                    {
                        "area": area["Name"],
                        "forecast": CODE_DESCRIPTION_MAP[
                            data_2_hour_weather_forecast["Item"]["WeatherForecast"][
                                "Area"
                            ][i]["Forecast"]
                        ],
                    }
                )
                i += 1

            return output

        def gen_24_hour_weather_forecast(self) -> dict:
            """
            Simulate response for _24-hour-weather-forecast_ endpoint
            """

            data_24_hour_weather_forecast = self.__weather.data.raw_resp["24hr"][
                "processed"
            ]["Channel24HrForecast"]
            update_datetime_24_hour = parser.parse(
                data_24_hour_weather_forecast["Main"]["ForecastIssue"]["DateTimeStr"]
            ).strftime("%Y-%m-%dT%H:%M:%S+08:00")
            valid_timestr_24_hour = data_24_hour_weather_forecast["Main"][
                "ValidTime"
            ].split(" - ")
            output = {
                "api_info": {"status": "healthy"},
                "items": [
                    {
                        "update_timestamp": update_datetime_24_hour,
                        "timestamp": update_datetime_24_hour,
                        "valid_period": {
                            "start": parser.parse(valid_timestr_24_hour[0]).strftime(
                                "%Y-%m-%dT%H:%M:%S+08:00"
                            ),
                            "end": parser.parse(valid_timestr_24_hour[1]).strftime(
                                "%Y-%m-%dT%H:%M:%S+08:00"
                            ),
                        },
                        "general": {
                            "forecast": data_24_hour_weather_forecast["Main"][
                                "Forecast"
                            ],
                            "relative_humidity": {
                                "low": data_24_hour_weather_forecast["Main"][
                                    "RelativeHumidity"
                                ]["Low"],
                                "high": data_24_hour_weather_forecast["Main"][
                                    "RelativeHumidity"
                                ]["High"],
                            },
                            "temperature": {
                                "low": data_24_hour_weather_forecast["Main"][
                                    "Temperature"
                                ]["Low"],
                                "high": data_24_hour_weather_forecast["Main"][
                                    "Temperature"
                                ]["High"],
                            },
                            "wind": {
                                "speed": {
                                    "low": data_24_hour_weather_forecast["Main"][
                                        "Wind"
                                    ]["Speed"].split(" - ")[0],
                                    "high": data_24_hour_weather_forecast["Main"][
                                        "Wind"
                                    ]["Speed"].split(" - ")[1],
                                },
                                "direction": data_24_hour_weather_forecast["Main"][
                                    "Wind"
                                ]["Direction"],
                            },
                        },
                        "periods": [],
                    }
                ],
            }

            for forecast in data_24_hour_weather_forecast["Forecasts"]:
                forecast_timeperiod = (
                    forecast["TimePeriod"]
                    .replace("Midday", "12 pm")
                    .replace("Midnight", "12 am")
                    .split(" to ")
                )
                period = {
                    "time": {
                        "start": parser.parse(forecast_timeperiod[0]).strftime(
                            "%Y-%m-%dT%H:%M:%S+08:00"
                        ),
                        "end": parser.parse(forecast_timeperiod[1]).strftime(
                            "%Y-%m-%dT%H:%M:%S+08:00"
                        ),
                    },
                    "regions": {
                        "west": CODE_DESCRIPTION_MAP[forecast["Wxwest"]],
                        "east": CODE_DESCRIPTION_MAP[forecast["Wxeast"]],
                        "central": CODE_DESCRIPTION_MAP[forecast["Wxcentral"]],
                        "south": CODE_DESCRIPTION_MAP[forecast["Wxsouth"]],
                        "north": CODE_DESCRIPTION_MAP[forecast["Wxnorth"]],
                    },
                }
                output["items"][0]["periods"].append(period)

            return output

        def gen_4_day_weather_forecast(self) -> dict:
            """
            Simulate response for _4-day-weather-forecast_ endpoint
            """

            data_4_day_weather_forecast = self.__weather.data.raw_resp["4day"][
                "processed"
            ]
            update_datetime_4_day = datetime.now().strftime(
                "%Y-%m-%dT%H:%M:%S+08:00"
            )  # NEA response does not include timestamp

            next_7_days_map = {}
            for i in range(7):
                date = datetime.now() + timedelta(days=i)
                next_7_days_map[(date.strftime("%a")).upper()] = date.strftime(
                    "%Y-%m-%dT00:00:00+08:00"
                )

            output = {
                "api_info": {"status": "healthy"},
                "items": [
                    {
                        "update_timestamp": update_datetime_4_day,
                        "timestamp": update_datetime_4_day,
                        "forecasts": [],
                    }
                ],
            }

            for forecast in data_4_day_weather_forecast:
                output["items"][0]["forecasts"].append(
                    {
                        "date": next_7_days_map[forecast["day"]][:10],
                        "timestamp": next_7_days_map[forecast["day"]],
                        "forecast": forecast["forecast"],
                        "relative_humidity": {
                            "low": math.nan,
                            "high": math.nan,
                        },  # no humidity forecast on weather.gov.sg or nea.gov.sg
                        "temperature": {
                            "low": forecast["temperature"].split(" - ")[0],
                            "high": forecast["temperature"].split(" - ")[1][:-2],
                        },
                        "wind": {
                            "speed": {
                                "low": forecast["wind_speed"]
                                .split(" - ")[0]
                                .split(" ")[1],
                                "high": forecast["wind_speed"].split(" - ")[1][:-5],
                            },
                            "direction": forecast["wind_speed"]
                            .split(" - ")[0]
                            .split(" ")[0],
                        },
                    }
                )

            return output

        def gen_realtime_weather(self, weather_type: str) -> dict:
            """
            Generalized generator to simulate API response for data.gov.sg realtime weather endpoints (except wind-direction)
            """
            if weather_type == "wind-direction":
                data = self.__weather.data.raw_resp["wind"]
            else:
                data = self.__weather.data.raw_resp[weather_type]

            output = {
                "api_info": {"status": "healthy"},
                "metadata": {
                    "stations": [],
                    "reading_type": REALTIME_WEATHER_CONST[weather_type][
                        "reading_type"
                    ],
                    "reading_unit": REALTIME_WEATHER_CONST[weather_type][
                        "reading_unit"
                    ],
                },
                "items": [
                    {
                        "timestamp": parser.parse(
                            data["obs_datetime"].replace("Observations at", "")
                        ).strftime("%Y-%m-%dT%H:%M:%S+08:00"),
                        "readings": [],
                    }
                ],
            }

            for station in data["processed"].keys():
                station_data = self.__weather.stations.__dict__[station]
                output["metadata"]["stations"].append(
                    {
                        "id": station,
                        "device_id": station,
                        "name": station_data["name"],
                        "location": {
                            "longitude": station_data["lon"],
                            "latitude": station_data["lat"],
                        },
                    }
                )
                if weather_type == "wind":
                    processed_value = (
                        float(station_data[weather_type]["value"]) * 0.539957
                    )  # convert km/h to knots
                elif weather_type == "wind-direction":
                    processed_value = WIND_DIR_TO_DEG_MAP[
                        station_data["wind"]["direction"]
                    ]  # direction str
                else:
                    processed_value = float(station_data[weather_type]["value"])

                if not math.isnan(processed_value):
                    output["items"][0]["readings"].append(
                        {
                            "station_id": station,
                            "value": processed_value,
                        }
                    )

            return output
