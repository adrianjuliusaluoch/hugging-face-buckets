# Production-like test: Supabase catalog (throwaway schema) + data files in the HF bucket
import os

import boto3
import duckdb
from botocore.config import Config
from dotenv import load_dotenv

load_dotenv()
NS, BUCKET = os.environ["HF_NAMESPACE"], os.environ["HF_BUCKET"]
KEY, SECRET = os.environ["HF_S3_KEY_ID"], os.environ["HF_S3_SECRET"]
PG = os.environ["PG_CATALOG"]
PREFIX = "scratch/hf-supabase-test/"
SCHEMA = "hf_test"

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
    return [o["Key"].removeprefix(PREFIX) for o in resp.get("Contents", [])]


con = duckdb.connect()
for ext in ("ducklake", "postgres", "httpfs"):
    con.execute(f"INSTALL {ext}")
    con.execute(f"LOAD {ext}")
con.execute(f"""
    CREATE OR REPLACE SECRET hf (
        TYPE s3, KEY_ID '{KEY}', SECRET '{SECRET}',
        ENDPOINT 's3.hf.co/{NS}', URL_STYLE 'path', REGION 'us-east-1'
    )
""")
con.execute(f"""
    ATTACH 'ducklake:postgres:{PG}' AS t (
        DATA_PATH 's3://{BUCKET}/{PREFIX}',
        METADATA_SCHEMA '{SCHEMA}',
        DATA_INLINING_ROW_LIMIT 0
    )
""")

con.execute("CREATE TABLE t.items (id BIGINT, name VARCHAR, views BIGINT, observed_at TIMESTAMPTZ)")
con.execute("INSERT INTO t.items SELECT range, 'item ' || range, 100, now() FROM range(400)")
print("1 insert 400 :", con.execute("SELECT COUNT(*) FROM t.items").fetchone(), "files:", len(files()))

# upsert: 50 existing rows change, 20 rows are new
con.execute("""
    CREATE TEMP TABLE changed AS
    SELECT range AS id, 'item ' || range AS name, 500 AS views, now() AS observed_at FROM range(50)
    UNION ALL
    SELECT range, 'item ' || range, 100, now() FROM range(400, 420)
""")
con.execute("BEGIN")
updated = con.execute("DELETE FROM t.items x WHERE EXISTS (SELECT 1 FROM changed c WHERE c.id = x.id)").fetchone()[0]
inserted = con.execute("INSERT INTO t.items SELECT * FROM changed").fetchone()[0]
con.execute("COMMIT")
print("2 upsert     :", updated, "deleted,", inserted, "inserted")
print("  expect (420, 50):", con.execute("SELECT COUNT(*), COUNT(*) FILTER (WHERE views = 500) FROM t.items").fetchone())
print("  files:", files())

con.execute("DROP TABLE t.items")
con.execute("CALL ducklake_expire_snapshots('t', older_than => now())")
con.execute("CALL ducklake_cleanup_old_files('t', cleanup_all => true)")
print("3 after cleanup, files left:", files())

con.execute("DETACH t")
for k in s3.list_objects_v2(Bucket=BUCKET, Prefix=PREFIX).get("Contents", []):
    s3.delete_object(Bucket=BUCKET, Key=k["Key"])
print("4 test prefix now holds", len(files()), "files")