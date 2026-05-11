import boto3
from botocore.client import Config
from io import BytesIO
import json

import os
from dotenv import load_dotenv

load_dotenv()

import logging

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s (%(name)s) : %(message)s"
)
log = logging.getLogger(__name__)

from src.scrape_site import scrape_site
from src.point_weather import request_weather_points


def upload_to_bucket(key, obj):
    try:
        if obj:
            json_bytes = json.dumps(
                obj, separators=(",", ":"), ensure_ascii=False
            ).encode("utf-8")

            r2_client.put_object(
                Bucket=os.environ["R2_BUCKET_NAME"],
                Body=BytesIO(json_bytes),
                Key=key,
                ContentType="application/json",
                CacheControl="public, max-age=3600, stale-while-revalidate=600",
            )
            log.info(f"Successfully uploaded '{key}' to R2 Bucket")
        else:
            log.warning("No weather object to upload")
    except Exception as e:
        log.error(f"Failed to upload '{key}' to R2 Bucket")
        log.error(e)


if __name__ == "__main__":
    log.info("Starting job.")

    log.info("Initialising boto3 client")
    r2_client = boto3.client(
        "s3",
        region_name="auto",
        endpoint_url=os.environ["R2_ENDPOINT_URL"],
        aws_access_key_id=os.environ["R2_ACCESS_KEY"],
        aws_secret_access_key=os.environ["R2_SECRET_KEY"],
        config=Config(signature_version="s3v4"),
    )

    # fetch weather data
    log.info("Starting the Lake District Weather retreival")
    weather = scrape_site()
    weather_points = request_weather_points()
    log.info("Finished the Lake District Weather retreival")

    # save json files to bucket
    log.info("Converting data and uploading to R2 Bucket")
    upload_to_bucket("weather.json", weather)
    upload_to_bucket("weather_points.json", weather_points)

    log.info("Finished job.")
