import boto3
from botocore.client import Config

import os
from dotenv import load_dotenv
import logging
import requests

from src.scrape_site import scrape_site
from src.point_weather import request_weather_points
from src.utils.r2_bucket import upload_to_bucket

load_dotenv()

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s (%(name)s) : %(message)s"
)
log = logging.getLogger(__name__)


def main(skip_scrape = False, skip_points = False):
    log.info("Starting job.")

    log.info("Connecting to boto3 client...")
    r2_client = boto3.client(
        "s3",
        region_name="auto",
        endpoint_url=os.environ["R2_ENDPOINT_URL"],
        aws_access_key_id=os.environ["R2_ACCESS_KEY"],
        aws_secret_access_key=os.environ["R2_SECRET_KEY"],
        config=Config(signature_version="s3v4"),
    )

    # met office weather
    if not skip_scrape:
        try:
            weather = scrape_site()
            upload_to_bucket(r2_client, "weather.json", weather)
        except RuntimeError:
            log.error("Something went wrong scraping Met Office weather.")

    # point-specific weather
    if not skip_points:
        try:
            weather_points = request_weather_points()
            upload_to_bucket(r2_client, "weather_points.json", weather_points)
        except requests.exceptions.HTTPError:
            log.error("Something went wrong requesting point-specific weather.")

    log.info("Job complete.")


if __name__ == "__main__":
    main()
