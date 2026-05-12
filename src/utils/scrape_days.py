from bs4 import Tag
from typing import Callable
import re

from src.utils.get_tags import (
    get_tag_by_class,
    get_all_tags_by_class,
    get_tag_in_tag,
    get_all_tags_in_tag,
    get_text_from_tag,
    get_text_from_p_in_class,
)


def forecast_row_parser(row: Tag) -> list[str]:
    values = []
    for td in [td for td in get_all_tags_in_tag(row, "td")]:
        td_text = get_text_from_tag(td)
        if len(td_text) > 0:
            values.append(td_text)
        else:
            inner_img = get_tag_in_tag(td, "img")
            if inner_img is not None:
                values.append(inner_img["alt"])

    return values


def wind_row_parser(row: Tag, parse_directions=False) -> list[str | int]:
    values = []
    for td in [td for td in get_all_tags_in_tag(row, "td")]:
        if parse_directions:
            inner_tag = get_tag_by_class(td, "direction")
            if inner_tag is not None:
                values.append(inner_tag["data-value"])
        else:
            wind_string = get_text_from_tag(get_tag_by_class(td, "wind-speed"))
            if len(wind_string) == 0:
                wind_string = get_text_from_tag(td)

            wind_mph = int(*re.findall(r"[0-9]+", wind_string))
            wind_kph = int(f"{(wind_mph * 1.60934):.0f}")
            values.append(wind_kph)

    return values


def temperature_row_parser(row: Tag) -> list[int]:
    values = []
    for td in [td for td in get_all_tags_in_tag(row, "td")]:
        if row["data-label"] == "height":
            freezing_level = int(*re.findall(r"[0-9]+", get_text_from_tag(td)))
            values.append(freezing_level)
        else:
            inner_span = get_tag_in_tag(td, "span")
            if inner_span is not None:
                values.append(int(inner_span["data-temp"]))

    return values


def get_all_rows_by_class(
    tag: Tag | None, table_class_name: str, row_parser: Callable
) -> dict[str, list[str | int]]:
    table_body = get_tag_in_tag(get_tag_by_class(tag, table_class_name), "tbody")

    table_rows = {}
    for row in get_all_tags_in_tag(table_body, "tr"):
        row_header = get_text_from_tag(get_tag_in_tag(row, "th"))
        table_rows[row_header] = row_parser(row)

    return table_rows


def get_all_rows_by_id(
    tag: Tag | None, table_id: str, row_parser: Callable
) -> dict[str, list[str | int]]:
    if tag is None:
        return {}

    table_body = get_tag_in_tag(tag.find(id=table_id), "tbody")

    table_rows = {}
    for row in get_all_tags_in_tag(table_body, "tr"):
        row_header = get_text_from_tag(get_tag_in_tag(row, "th"))
        table_rows[row_header] = row_parser(row)

    return table_rows


def parse_forecast_tables(mountain_forecast: Tag | None):
    if mountain_forecast is None:
        return None

    time = [
        get_text_from_tag(td)
        for td in get_all_tags_in_tag(
            get_tag_in_tag(
                get_tag_by_class(mountain_forecast, "mountain-forecast-table"), "thead"
            ),
            "td",
        )
    ]
    forecast_rows = get_all_rows_by_class(
        mountain_forecast, "mountain-forecast-table", forecast_row_parser
    )
    wind_rows = get_all_rows_by_id(
        mountain_forecast, "wind-speed-table", wind_row_parser
    )
    wind_dir_rows = get_all_rows_by_id(
        mountain_forecast,
        "wind-speed-table",
        lambda row: wind_row_parser(row, parse_directions=True),
    )
    wind_gust_rows = get_all_rows_by_id(
        mountain_forecast, "wind-gust-table", wind_row_parser
    )
    temperature_rows = get_all_rows_by_class(
        mountain_forecast.find(id="accordion-panel-temperature"),
        "temperature-table",
        temperature_row_parser,
    )
    feelslike_temperature_rows = get_all_rows_by_class(
        mountain_forecast.find(id="accordion-panel-feelsLike-temperature"),
        "temperature-table",
        temperature_row_parser,
    )
    del feelslike_temperature_rows["Freezing Level"]

    return {
        "time": time,
        "type": forecast_rows["Weather (at 800m)"],
        "precip": forecast_rows["Chance of precipitation (at 800m)"],
        "wind_speed_kph": wind_rows,
        "wind_gust_kph": wind_gust_rows,
        "wind_dir": wind_dir_rows,
        "temp_c": temperature_rows,
        "feel_temp_c": feelslike_temperature_rows,
    }


def parse_evening_weather(evening_summary: Tag, tab_info):
    summary = get_text_from_tag(evening_summary)

    return {
        "type": "this-evening",
        "sunrise": tab_info["sunrise"],
        "sunset": tab_info["sunset"],
        "summary": summary,
    }


def parse_current_weather(mountain_forecast: Tag, tab_info):
    meteorologist_view = get_text_from_p_in_class(
        mountain_forecast, "meteorologist-view"
    )

    mountain_hazard_groups = get_all_tags_by_class(
        get_tag_by_class(mountain_forecast, "mountain-hazard"), "accordion"
    )
    hazard_levels = [
        get_text_from_tag(get_tag_by_class(group, "accordion-header")).split()[0].strip().lower()
        for group in mountain_hazard_groups
    ]
    hazard_hazards = [
        [
            get_text_from_tag(header)
            for header in get_all_tags_by_class(group, "hazard-header")
        ]
        for group in mountain_hazard_groups
    ]
    hazards = {hazard_levels[i]: hazard_hazards[i] for i in range(len(hazard_levels))}

    weather = get_text_from_p_in_class(mountain_forecast, "weather")
    cloud_free_top = get_text_from_p_in_class(mountain_forecast, "cloud-free-top")
    visibility = get_text_from_p_in_class(mountain_forecast, "visibility")
    weather_forecast = get_text_from_p_in_class(mountain_forecast, "weather-forecast")

    forecast = parse_forecast_tables(mountain_forecast)

    return {
        "type": "current-day",
        "date": tab_info["date"],
        "sunrise": tab_info["sunrise"],
        "sunset": tab_info["sunset"],
        "tagline": weather_forecast,
        "summary": weather,
        "cloud_free_top": cloud_free_top,
        "visibility": visibility,
        "meteorologist_view": meteorologist_view,
        "hazards": hazards,
        "forecast": forecast,
    }


def parse_tomorrow_weather(mountain_additional_info: Tag, tab_info):
    weather = get_text_from_p_in_class(mountain_additional_info, "weather")
    cloud_free_top = get_text_from_p_in_class(
        mountain_additional_info, "cloud-free-top"
    )
    max_wind = get_text_from_p_in_class(mountain_additional_info, "max-wind")
    visibility = get_text_from_p_in_class(mountain_additional_info, "visibility")

    temperature = {}
    for li in get_all_tags_in_tag(
        get_tag_by_class(mountain_additional_info, "temperature"), "li"
    ):
        li_title = get_text_from_tag(get_tag_in_tag(li, "span"))
        li_content = get_text_from_tag(li).replace(li_title, "").strip()
        temperature[li_title] = li_content

    return {
        "type": "tomorrows-tab",
        "date": tab_info["date"],
        "sunrise": tab_info["sunrise"],
        "sunset": tab_info["sunset"],
        "summary": weather,
        "cloud_free_top": cloud_free_top,
        "max_wind": max_wind,
        "temperature": temperature,
        "visibility": visibility,
    }


def parse_further_outlook(further_outlook: Tag):
    days = get_all_tags_by_class(further_outlook, "outlook-day")

    further_days = []
    for day in days:
        day_data = {}

        day_data["date"] = get_text_from_tag(get_tag_in_tag(day, "h4"))

        sunshine = get_all_tags_by_class(day, "sun-row")
        day_data["sunrise"] = get_text_from_tag(get_tag_in_tag(sunshine[0], "time"))
        day_data["sunset"] = get_text_from_tag(get_tag_in_tag(sunshine[1], "time"))

        day_data["summary"] = get_text_from_tag(get_tag_in_tag(day, "p"))

        further_days.append(day_data)

    return {
        "type": "further-outlook",
        "days": further_days,
    }
