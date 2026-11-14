# Upload and download files in the Hugging Face bucket (it speaks the S3 language)
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from . import config


def client():
    return boto3.client(
        "s3",
        endpoint_url=f"https://{config.HF_NAMESPACE}.s3.hf.co",
        aws_access_key_id=config.HF_S3_KEY_ID,
        aws_secret_access_key=config.HF_S3_SECRET,
        config=Config(
            region_name="us-east-1",
            s3={"addressing_style": "path"},
            # the gateway can't parse the checksums newer boto3 sends by default
            request_checksum_calculation="when_required",
            response_checksum_validation="when_required",
        ),
    )


def upload(local_path, key):
    client().upload_file(str(local_path), config.HF_BUCKET, key)


def download_if_exists(key, local_path):
    # Returns False when the file is not in the bucket yet (first run)
    try:
        client().download_file(config.HF_BUCKET, key, str(local_path))
        return True
    except ClientError as e:
        if e.response["Error"]["Code"] in ("404", "NoSuchKey", "NotFound"):
            return False
        raise