"""Download the FinanceBench PDFs into a Unity Catalog volume.

Task `download` of the job `ingest_financebench`. Creates the bronze schema and its `docs` volume, then downloads
every PDF in the `pdfs/` folder of patronus-ai/financebench into `/Volumes/workspace/finance_bench_bronze/docs/pdfs`.
Files already in the volume are skipped.

Usage: python download.py [--match <regex>] [--limit <n>]

`--match` keeps only the PDFs whose file name matches the regex, and `--limit` keeps only the first n of them
(0 = all). They are the only parameters, because dev and prod need different values: dev downloads a small sample,
so a dev run parses only a few PDFs.
"""

import argparse
import logging
import os
import re

import requests
from pyspark.sql import SparkSession

CATALOG = "workspace"
BRONZE_SCHEMA_NAME = "finance_bench_bronze"
BRONZE_SCHEMA = f"{CATALOG}.{BRONZE_SCHEMA_NAME}"
PDFS_DIR = f"/Volumes/{CATALOG}/{BRONZE_SCHEMA_NAME}/docs/pdfs"
PDF_LIST_URL = "https://api.github.com/repos/patronus-ai/financebench/contents/pdfs"

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-7s | %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger("download")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--match", default=".*", help="only PDFs whose file name matches this regex")
    parser.add_argument("--limit", type=int, default=0, help="only the first n PDFs (0 = all)")
    args = parser.parse_args()

    # Assets: the schema and the volume.
    spark = SparkSession.builder.getOrCreate()
    spark.sql(f"CREATE CATALOG IF NOT EXISTS {CATALOG}")
    spark.sql(f"CREATE SCHEMA IF NOT EXISTS {BRONZE_SCHEMA}")
    spark.sql(f"CREATE VOLUME IF NOT EXISTS {BRONZE_SCHEMA}.docs")
    os.makedirs(PDFS_DIR, exist_ok=True)

    # The PDFs in the repository (one unauthenticated GitHub API call), then the sample.
    resp = requests.get(PDF_LIST_URL, timeout=60)
    resp.raise_for_status()
    pdfs = [(f["name"], f["download_url"]) for f in resp.json() if f["name"].lower().endswith(".pdf")]
    pdfs = [(name, url) for name, url in pdfs if re.search(args.match, name)]
    if args.limit:
        pdfs = pdfs[: args.limit]
    log.info("%d PDFs to download (match=%r, limit=%d)", len(pdfs), args.match, args.limit)

    # Download the ones not in the volume yet.
    for i, (name, url) in enumerate(pdfs, start=1):
        dest = f"{PDFS_DIR}/{name}"
        if os.path.exists(dest) and os.path.getsize(dest) > 0:
            continue
        r = requests.get(url, timeout=120)
        r.raise_for_status()
        with open(dest, "wb") as f:
            f.write(r.content)
        log.info("[%d/%d] downloaded %s (%.1f MB)", i, len(pdfs), name, len(r.content) / 1e6)


if __name__ == "__main__":
    main()
