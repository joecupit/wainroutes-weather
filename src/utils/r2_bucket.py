from io import BytesIO
import json
import os
import logging

log = logging.getLogger(__name__)


def upload_to_bucket(r2_client, key: str, json_data: dict):
    try:
        json_bytes = json.dumps(
            json_data, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")

        r2_client.put_object(
            Bucket=os.environ["R2_BUCKET_NAME"],
            Body=BytesIO(json_bytes),
            Key=key,
            ContentType="application/json",
            CacheControl="public, max-age=3600, stale-while-revalidate=600",
        )
        log.info(f"Successfully uploaded '{key}' to R2 Bucket")
    except Exception as e:
        log.error(f"Failed to upload '{key}' to R2 Bucket")
        log.error(e)
