import requests
import json
from datetime import datetime

import os
from dotenv import load_dotenv

load_dotenv()

import logging

log = logging.getLogger(__name__)


WEATHER_TYPES = {
    "NA": "Not available",
    -1: "Trace rain",
    0: "Clear night",
    1: "Sunny day",
    2: "Partly cloudy (night)",
    3: "Partly cloudy (day)",
    4: "Not used",
    5: "Mist",
    6: "Fog",
    7: "Cloudy",
    8: "Overcast",
    9: "Light rain shower (night)",
    10: "Light rain shower (day)",
    11: "Drizzle",
    12: "Light rain",
    13: "Heavy rain shower (night)",
    14: "Heavy rain shower (day)",
    15: "Heavy rain",
    16: "Sleet shower (night)",
    17: "Sleed shower (day)",
    18: "Sleet",
    19: "Hail shower (night)",
    20: "Hail shower (day)",
    21: "Hail",
    22: "Light snow shower (night)",
    23: "Light snow shower (day)",
    24: "Light snow",
    25: "Heavy snow shower (night)",
    26: "Heavy snow shower (day)",
    27: "Heavy snow",
    28: "Thunder shower (night)",
    29: "Thunder shower (day)",
    30: "Thunder",
}


def get_weather_at_point(
    latitude: float,
    longitude: float,
    excludeParameterMetadata: bool = True,
    includeLocationName: bool = True,
):
    query_params = []
    if excludeParameterMetadata:
        query_params.append("excludeParameterMetadata=true")
    if includeLocationName:
        query_params.append("includeLocationName=true")

    query_params.append("latitude=" + str(latitude))
    query_params.append("longitude=" + str(longitude))

    query_url = os.environ["MET_OFFICE_API_URL"] + "?" + "&".join(query_params)

    headers = {"accept": "application/json", "apiKey": os.environ["MET_OFFICE_API_KEY"]}

    response = requests.get(query_url, headers=headers)
    if response.ok:
        return parse_weather_at_point(response.json())
    else:
        log.error(
            "Failed to get point weather - Error code " + str(response.status_code)
        )
        log.error(response.raise_for_status())
        return {}


def parse_weather_at_point(weather_data: dict):
    data = weather_data["features"][0]

    coordinates = data["geometry"]["coordinates"]
    lon_lat = [coordinates[0], coordinates[1]]
    elevation = int(coordinates[2])

    properties = data["properties"]
    loc_name = properties["location"]["name"]
    req_date = date_from_string(properties["modelRunDate"])

    parsed_data = {
        "request_date": str(req_date),
        "name": loc_name + " Summit",
        "elevation": elevation,
        "coordinates": lon_lat,
    }

    parsed_days = []

    days = properties["timeSeries"]
    for day in days:
        if (date := date_from_string(day["time"])) < req_date:
            continue

        day_precipitation_types = {
            "rain": day["dayProbabilityOfRain"],
            "snow": day["dayProbabilityOfSnow"],
            "hail": day["dayProbabilityOfHail"],
        }
        day_predominant_precipitaion_type = max(
            day_precipitation_types.keys(), key=lambda k: day_precipitation_types[k]
        )
        night_precipitation_types = {
            "rain": day["nightProbabilityOfRain"],
            "snow": day["nightProbabilityOfSnow"],
            "hail": day["nightProbabilityOfHail"],
        }
        night_predominant_precipitaion_type = max(
            night_precipitation_types.keys(), key=lambda k: night_precipitation_types[k]
        )

        day_data = {
            "date": str(date),
            "weather_type": [
                WEATHER_TYPES[day["daySignificantWeatherCode"]],
                WEATHER_TYPES[day["nightSignificantWeatherCode"]],
            ],
            "temp": {
                "screen": [
                    int(day["dayMaxScreenTemperature"]),
                    int(day["nightMinScreenTemperature"]),
                ],
                "max": [
                    int(day["dayUpperBoundMaxTemp"]),
                    int(day["nightUpperBoundMinTemp"]),
                ],
                "min": [
                    int(day["dayLowerBoundMaxTemp"]),
                    int(day["nightLowerBoundMinTemp"]),
                ],
                "feels": [
                    int(day["dayMaxFeelsLikeTemp"]),
                    int(day["nightMinFeelsLikeTemp"]),
                ],
            },
            "precipitation": {
                "prob": [
                    day["dayProbabilityOfPrecipitation"],
                    day["nightProbabilityOfPrecipitation"],
                ],
                "type": [
                    day_predominant_precipitaion_type,
                    night_predominant_precipitaion_type,
                ],
            },
            "wind": {
                "speed": [
                    meters_per_second_to_kilometers_per_hour(day["midday10MWindSpeed"]),
                    meters_per_second_to_kilometers_per_hour(
                        day["midnight10MWindSpeed"]
                    ),
                ],
                "gusts": [
                    meters_per_second_to_kilometers_per_hour(day["midday10MWindGust"]),
                    meters_per_second_to_kilometers_per_hour(
                        day["midnight10MWindGust"]
                    ),
                ],
            },
            "visibility": {
                "m": [day["middayVisibility"], day["midnightVisibility"]],
                "text": [
                    define_visibility_type(day["middayVisibility"]),
                    define_visibility_type(day["midnightVisibility"]),
                ],
            },
        }

        parsed_days.append(day_data)

    parsed_data["days"] = parsed_days

    return parsed_data


def date_from_string(date_string: str):
    return datetime.strptime(date_string, "%Y-%m-%dT%H:%MZ").date()


def meters_per_second_to_kilometers_per_hour(mps: float) -> float:
    kilometers_per_second = mps / 1000
    kilometers_per_hour = kilometers_per_second * 60 * 60
    return int(kilometers_per_hour)


def define_visibility_type(visibility: int):
    visibility_km = visibility / 1000

    if visibility_km < 1:
        return "Very poor"
    if visibility_km < 4:
        return "Poor"
    if visibility_km < 10:
        return "Moderate"
    if visibility_km < 20:
        return "Good"
    if visibility_km < 40:
        return "Very Good"

    return "Excellent"


def request_weather_points(save_local=False):
    result = {}

    log.info("Requesting point-specific weather data...")
    with open("src/assets/locations.json", "r") as f:
        for loc in json.load(f):
            result[loc["name"]] = get_weather_at_point(
                loc["coords"][0], loc["coords"][1]
            )

    if save_local:
        log.info("Saving weather_points.json as a local file")
        with open("weather_points.json", "w") as f:
            json.dump(result, f, indent=2)

    return result


if __name__ == "__main__":
    request_weather_points(save_local=True)
