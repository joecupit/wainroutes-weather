from bs4 import BeautifulSoup, Tag
import requests
import os
import logging
import json
from dotenv import load_dotenv
from datetime import datetime

from utils.get_tags import (
    get_tag_by_class,
    get_tag_in_tag,
    get_all_tags_in_tag,
    get_text_from_tag,
)
from utils.scrape_days import (
    parse_evening_weather,
    parse_current_weather,
    parse_tomorrow_weather,
    parse_further_outlook,
)

load_dotenv()
log = logging.getLogger(__name__)


def request_met_site() -> Tag | None:
    log.info("Scraping Met Office weather data")
    response = requests.get(os.environ["MET_OFFICE_WEATHER_URL"])
    if response.status_code != 200:
        log.error(f"Failed to retrieve data. Status code: {response.status_code}")
        return

    html = response.content.decode("utf-8")
    return BeautifulSoup(html, "html.parser")


def parse_days(soup: Tag):
    tabs = get_all_tags_in_tag(
        get_tag_in_tag(get_tag_by_class(soup, "tabbed-forecast-tabs"), "ul"), "li"
    )

    days = []
    for tab in tabs:
        day_id = tab["aria-controls"]
        day_date = tab["data-datefrom"]

        sunrise = get_text_from_tag(
            get_tag_in_tag(get_tag_by_class(tab, "sunrise"), "time")
        )
        sunset = get_text_from_tag(
            get_tag_in_tag(get_tag_by_class(tab, "sunset"), "time")
        )

        tab_info = {
            "date": day_date,
            "sunrise": sunrise,
            "sunset": sunset,
        }

        day = soup.find(id=day_id)

        evening_summary = get_tag_by_class(day, "evening-summary")
        if evening_summary is not None:
            days.append(parse_evening_weather(evening_summary, tab_info))
            continue

        mountain_forecast = get_tag_by_class(day, "mountain-forecast")
        if mountain_forecast is not None:
            days.append(parse_current_weather(mountain_forecast, tab_info))
            continue

        mountain_additional_info = get_tag_by_class(day, "mountain-additional-info")
        if mountain_additional_info is not None:
            days.append(parse_tomorrow_weather(mountain_additional_info, tab_info))
            continue

        further_outlook = get_tag_by_class(day, "further-outlook")
        if further_outlook is not None:
            days.append(parse_further_outlook(further_outlook))
            continue

    return days


def scrape_site(save_local=False):
    soup = request_met_site()
    if soup is None:
        raise RuntimeError("No site data to scrape.")
    request_time = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")

    # find forecast issue time
    issue_time_tag = get_tag_in_tag(get_tag_by_class(soup, "issued-time"), "time")
    if issue_time_tag is not None:
        issue_time = issue_time_tag["datetime"]
    else:
        issue_time = "N/A"

    # find forecast accuracy confidence
    confidence_tag = get_tag_in_tag(get_tag_by_class(soup, "confidence"), "p")
    if confidence_tag is not None:
        confidence = get_text_from_tag(confidence_tag)
    else:
        confidence = "Not available."

    # scrape all available days
    days = parse_days(soup)

    weather_data = {
        "issue_time": issue_time,
        "confidence": confidence,
        "days": days,
        "update_time": request_time,
    }

    if save_local:
        log.info("Saving weather.json as a local file")
        with open("weather.json", "w") as f:
            json.dump(weather_data, f, indent=2)

    return weather_data


if __name__ == "__main__":
    weather_data = scrape_site(save_local=True)
    print(weather_data)
