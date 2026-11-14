# Throwaway test: DuckLake with a local catalog file and data files in the HF bucket
import os

import boto3
import duckdb
from botocore.config import Config
from dotenv import load_dotenv

load_dotenv()
NS, BUCKET = os.environ["HF_NAMESPACE"], os.environ["HF_BUCKET"]
KEY, SECRET = os.environ["HF_S3_KEY_ID"], os.environ["HF_S3_SECRET"]
PREFIX = "scratch/ducklake-test/"

s3 = boto3.client(
    "s3",
    endpoint_url=f"https://{NS}.s3.hf.co",
    aws_access_key_id=KEY,
    aws_secret_access_key=SECRET,
    config=Config(
        region_name="us-east-1",
        s3={"addressing_style": "path"},
        request_checksum_calculation="when_required",
        response_checksum_validation="when_required",
    ),
)


def files():
    resp = s3.list_objects_v2(Bucket=BUCKET, Prefix=PREFIX)
    return [o["Key"] for o in resp.get("Contents", [])]


con = duckdb.connect()
for ext in ("ducklake", "httpfs"):
    con.execute(f"INSTALL {ext}")
    con.execute(f"LOAD {ext}")
con.execute(f"""
    CREATE OR REPLACE SECRET hf (
        TYPE s3, KEY_ID '{KEY}', SECRET '{SECRET}',
        ENDPOINT 's3.hf.co/{NS}', URL_STYLE 'path', REGION 'us-east-1'
    )
""")
con.execute(f"ATTACH 'ducklake:hf_test.ducklake' AS t (DATA_PATH 's3://{BUCKET}/{PREFIX}')")

con.execute("CREATE TABLE t.x AS SELECT range AS id, 'a' AS v FROM range(1000)")
print("1 write+read :", con.execute("SELECT COUNT(*) FROM t.x").fetchone())
print("  bucket files:", files())

con.execute("UPDATE t.x SET v = 'b' WHERE id < 10")
print("2 update     :", con.execute("SELECT v, COUNT(*) FROM t.x GROUP BY 1 ORDER BY 1").fetchall())

con.execute("DELETE FROM t.x WHERE id >= 990")
print("3 delete     :", con.execute("SELECT COUNT(*) FROM t.x").fetchone())
print("  bucket files:", len(files()))

con.execute("DROP TABLE t.x")
con.execute("CALL ducklake_expire_snapshots('t', older_than => now())")
con.execute("CALL ducklake_cleanup_old_files('t', cleanup_all => true)")
print("4 after cleanup, files left:", files())

con.execute("DETACH t")

# remove anything the cleanup left behind, limited to the test prefix
for k in files():
    s3.delete_object(Bucket=BUCKET, Key=k)
print("5 test prefix now holds", len(files()), "files")