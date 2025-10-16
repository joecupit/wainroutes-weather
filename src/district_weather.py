import json
import requests
from bs4 import BeautifulSoup, ResultSet, Tag

import os
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()

import logging
log = logging.getLogger(__name__)


def scrape_met_site(save_local=False):
  log.info("Scraping Met Office weather data")
  response = requests.get(os.environ["MET_OFFICE_WEATHER_URL"])
  if response.status_code != 200:
    log.error(f"Failed to retrieve data. Status code: {response.status_code}")
    return

  soup = BeautifulSoup(response.content, "html.parser")
  scraped = scrape_soup(soup)

  if save_local:
    log.info("Saving weather.json as a local file")
    with open("weather.json", "w") as f:
      json.dump(scraped, f, indent=2)

  return scraped


def scrape_soup(soup: BeautifulSoup):
  weather_data = dict()

  weather_data["issue_time"] = get_tag_text_by_class(soup, "issue-time", "time")
  weather_data["confidence"] = get_p_text_by_class(soup, "confidence")

  days = []
  for day_n in ["day0", "day1", "day2", "day3"]:
    day = soup.find(id=day_n)
    if isinstance(day, Tag):
      days.append(scrape_day(day))
  weather_data["days"] = days

  weather_data["update_time"] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

  return weather_data


def get_suntime(suntime: ResultSet):
  return {
    "sunrise": suntime[0].find("time").text.strip(),
    "sunset": suntime[1].find("time").text.strip()
  }


def get_tag_text_by_class(tag: Tag, class_name: str, tag_name: str):
  inner_tag = tag.find(class_=class_name)
  if not isinstance(inner_tag, Tag): return None

  p_tag = inner_tag.find(tag_name)
  if not isinstance(p_tag, Tag): return None

  return " ".join(p_tag.text.strip().split())


def get_p_text_by_class(tag: Tag, class_name: str):
  return get_tag_text_by_class(tag, class_name, tag_name="p")


def get_temperature_data(tag: Tag, class_name: str):
  temperature_data : dict[str, str] = dict()

  result = tag.find(class_=class_name)
  if not isinstance(result, Tag): return None

  result_2 = result.find("ul")
  if not isinstance(result_2, Tag): return None

  for li in result_2.find_all("li"):
    li_title = li.find("span").text.strip()
    temperature_data[li_title] = li.text.replace(li_title, "").strip()

  return temperature_data


def get_td_from_row_in_table_by_class(parent: Tag, class_name: str, rowN: int = 0, fromHead: bool = False):
  container = parent.find(class_=class_name)
  if not isinstance(container, Tag): return []

  table = container.find("table")
  if not isinstance(table, Tag): return []

  tbody = table.find("tbody" if (not fromHead) else "thead")
  if not isinstance(tbody, Tag): return []

  rows = tbody.find_all("tr")
  if not isinstance(rows, ResultSet): return []

  return rows[rowN].find_all("td" if (not fromHead) else "th")


def scrape_day_forecast(forecast: Tag):
  weather_row = get_td_from_row_in_table_by_class(forecast, "weather-table", fromHead=True)
  times = [t.text.strip() for t in weather_row[1:]]

  weather_types = [d.find("img")["alt"] for d in get_td_from_row_in_table_by_class(forecast, "weather-table")]
  precip_chances = [d.text.strip() for d in get_td_from_row_in_table_by_class(forecast, "weather-table", rowN=1)]


  wind_row = get_td_from_row_in_table_by_class(forecast, "wind-table")
  wind_speeds = [w.find(class_="speed").text.strip() for w in wind_row]
  wind_dirs = [w.find("span")["data-value"] for w in wind_row]

  wind_gust_row = get_td_from_row_in_table_by_class(forecast, "wind-gust-table")
  wind_gusts = [w.text.strip() for w in wind_gust_row]


  temp_row = get_td_from_row_in_table_by_class(forecast, "temperature-table")
  temps = [t["data-temp"] for t in temp_row]

  temp_feels_row = get_td_from_row_in_table_by_class(forecast, "feels-temperature-table")
  temp_feels = [t["data-temp"] for t in temp_feels_row]

  # trim all lists to only include data from 06:00 onwards
  six_am = times.index("06:00")
  if (six_am > 0):
    times = times[six_am:]
    weather_types = weather_types[six_am:]
    precip_chances = ["<5%" if p == "<05%" else p for p in precip_chances[six_am:]]
    wind_speeds = wind_speeds[six_am:]
    wind_gusts = wind_gusts[six_am:]
    wind_dirs = wind_dirs[six_am:]
    temps = temps[six_am:]
    temp_feels = temp_feels[six_am:]

  return {
    "time": times,
    "type": weather_types,
    "precip": precip_chances,
    "wind_speed": wind_speeds,
    "wind_gust": wind_gusts,
    "wind_dir": wind_dirs,
    "temp": temps,
    "feel_temp": temp_feels
  }


def scrape_hazard_level(hazard_details: Tag):
  hazards = [hazard.text.strip() for hazard in hazard_details.find_all(class_="hazard-header")]
  hazards_desc = [desc.text.strip().replace("\u00e2\u20ac\u02dc", "'").replace("\u00e2\u20ac\u2122", "'") for desc in hazard_details.find_all(class_="hazard-description")]
  return {hazards[i]: hazards_desc[i] for i in range(len(hazards))}

def scrape_hazards(mountain_hazard: Tag):
  hazard_accordian = mountain_hazard.find(id="accordion-group")
  if not isinstance(hazard_accordian, Tag): return {}

  levels = [level.text.split()[0].strip().lower() for level in hazard_accordian.find_all(class_="accordion-header")]
  hazard_details = [details for details in hazard_accordian.find_all(class_="accordion-panel")]

  return {levels[i]: scrape_hazard_level(hazard_details[i]) for i in range(len(levels))}


def scrape_day(day: Tag):
  day_weather = dict()

  day_classes = [c for c in day["class"] if c not in ["tab-content", "no-js-block"]]
  day_type = day_classes[-1] if len(day_classes) > 0 else "current-day"
  day_weather["type"] = day_type

  if day_type != "further-outlook":
    if day_type != "this-evening":
      day_weather["date"] = day["data-content-id"]
    day_weather = day_weather | get_suntime(day.find_all(class_="sunrise-sunset"))


  if day_type == "current-day":

    hazard_details = day.find(class_="mountain-hazard")
    if isinstance(hazard_details, Tag):
      day_weather["hazards"] = scrape_hazards(hazard_details)

    day_details = day.find(class_="mountain-additional-info")
    if isinstance(day_details, Tag):
      day_weather["meteorologist_view"] = get_p_text_by_class(day_details, "meteorologist-view")
      day_weather["summary"] = get_p_text_by_class(day_details, "weather")
      day_weather["cloud_free_top"] = get_p_text_by_class(day_details, "cloud-free-top")
      day_weather["visibility"] = get_p_text_by_class(day_details, "visibility")
      day_weather["ground_conditions"] = get_p_text_by_class(day_details, "ground-conditions")

    day_forecast = day.find(class_="mountain-forecast")
    if isinstance(day_forecast, Tag):
      day_weather["weather"] = get_p_text_by_class(day_forecast, "weather-forecast")
      day_weather["forecast"] = scrape_day_forecast(day_forecast)

  elif day_type == "tomorrows-tab":

    day_details = day.find(class_="mountain-additional-info")
    if isinstance(day_details, Tag):
      day_weather["summary"] = get_p_text_by_class(day_details, "weather")
      day_weather["cloud_free_top"] = get_p_text_by_class(day_details, "cloud-free-top")
      day_weather["max_wind"] = get_p_text_by_class(day_details, "max-wind")
      day_weather["temperature"] = get_temperature_data(day_details, "temperature")
      day_weather["visibility"] = get_p_text_by_class(day_details, "visibility")

  elif day_type == "this-evening":

    day_details = day.find(class_="evening-summary")
    if isinstance(day_details, Tag):
      day_details_p_tag = day_details.find("p")
      if isinstance(day_details_p_tag, Tag):
        day_weather["summary"] = day_details_p_tag.text.strip()

  elif day_type == "further-outlook":
    outlook_list = []
    for outlook in day.find_all(class_="outlook-day"):
      outlook_list.append({
        "date": outlook.find("h4").text.strip()}
        | get_suntime(outlook.find_all(class_="sunrise-sunset"))
        | {"summary": outlook.find("p").text.strip()}
      )
    day_weather["days"] = outlook_list

  return day_weather


if __name__ == "__main__":
  scrape_met_site(save_local=True)
