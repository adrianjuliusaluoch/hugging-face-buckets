# Lake maintenance: merge small files, expire old versions, delete the leftovers.
# Without --run it only shows what expiry and cleanup would remove.
import argparse

from . import config, lake, storage

PREFIX = "lake/weather/"


def count_files():
    pages = storage.client().get_paginator("list_objects_v2").paginate(
        Bucket=config.HF_BUCKET, Prefix=PREFIX
    )
    keys = [o for p in pages for o in p.get("Contents", [])]
    return len(keys), sum(o["Size"] for o in keys)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--days", type=int, default=7, help="keep this many days of versions")
    p.add_argument("--run", action="store_true", help="actually merge, expire and delete")
    a = p.parse_args()

    n, size = count_files()
    print(f"before: {n} files, {size / 1e3:.1f} kB under {PREFIX}")

    con = lake.connect()
    dry = "" if a.run else ", dry_run => true"

    if a.run:
        print("merge small files:")
        print("  ", con.execute("CALL ducklake_merge_adjacent_files('weather_lake')").fetchall())
    else:
        print("merge small files: skipped in a dry run")

    print("expire snapshots:")
    for row in con.execute(
        f"CALL ducklake_expire_snapshots('weather_lake', older_than => now() - INTERVAL '{a.days} days'{dry})"
    ).fetchall():
        print("  ", row)

    print("clean up files:")
    for row in con.execute(
        f"CALL ducklake_cleanup_old_files('weather_lake', cleanup_all => true{dry})"
    ).fetchall():
        print("  ", row)

    con.execute("DETACH weather_lake")
    con.close()

    if a.run:
        n, size = count_files()
        print(f"after: {n} files, {size / 1e3:.1f} kB under {PREFIX}")
    else:
        print("dry run, nothing changed. Add --run to apply.")


if __name__ == "__main__":
    main()