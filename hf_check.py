# Upload, list, read and delete one tiny file in the bucket
import os

import boto3
from botocore.config import Config
from dotenv import load_dotenv

load_dotenv()
NS, BUCKET = os.environ["HF_NAMESPACE"], os.environ["HF_BUCKET"]

s3 = boto3.client(
    "s3",
    endpoint_url=f"https://{NS}.s3.hf.co",
    aws_access_key_id=os.environ["HF_S3_KEY_ID"],
    aws_secret_access_key=os.environ["HF_S3_SECRET"],
    config=Config(
        region_name="us-east-1",
        s3={"addressing_style": "path"},
        request_checksum_calculation="when_required",
        response_checksum_validation="when_required",
    ),
)

key = "scratch/hello.txt"
s3.put_object(Bucket=BUCKET, Key=key, Body=b"hello from the pipeline")
print("listed:", [o["Key"] for o in s3.list_objects_v2(Bucket=BUCKET, Prefix="scratch/").get("Contents", [])])
print("read  :", s3.get_object(Bucket=BUCKET, Key=key)["Body"].read())
s3.delete_object(Bucket=BUCKET, Key=key)
print("after delete:", s3.list_objects_v2(Bucket=BUCKET, Prefix="scratch/").get("KeyCount"), "objects")