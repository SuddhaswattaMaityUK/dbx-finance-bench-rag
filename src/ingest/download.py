"""Ingest raw FinanceBench PDFs into a Unity Catalog volume.

Creates the bronze schema and its `docs` volume if they don't exist, then downloads every PDF from the
patronus-ai/financebench `pdfs/` folder into the volume. Files already in the volume are skipped.

Usage: python download.py --catalog <catalog> --bronze-schema <schema> [--match <regex>] [--limit <n>]

`--match` keeps only the PDFs whose file name matches the regex, and `--limit` keeps only the first n of
those (0 = all). Dev uses them to download a small sample.
"""

import argparse
import logging
import os
import re

import requests
from pyspark.sql import SparkSession

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("download")

PDF_LIST_URL = "https://api.github.com/repos/patronus-ai/financebench/contents/pdfs"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", required=True)
    parser.add_argument("--bronze-schema", required=True)
    parser.add_argument("--match", default=".*", help="only PDFs whose file name matches this regex")
    parser.add_argument("--limit", type=int, default=0, help="only the first n PDFs (0 = all)")
    args = parser.parse_args()
    catalog, schema = args.catalog, args.bronze_schema

    log.info("Target: catalog=%s schema=%s", catalog, schema)
    spark = SparkSession.builder.getOrCreate()
    log.info("Ensuring schema and volume exist")
    spark.sql(f"CREATE SCHEMA IF NOT EXISTS {catalog}.{schema}")
    spark.sql(f"CREATE VOLUME IF NOT EXISTS {catalog}.{schema}.docs")

    pdf_dir = f"/Volumes/{catalog}/{schema}/docs/pdfs"
    os.makedirs(pdf_dir, exist_ok=True)

    # List every PDF in the repo (one unauthenticated GitHub API call).
    resp = requests.get(PDF_LIST_URL, timeout=60)
    resp.raise_for_status()
    pdfs = [(f["name"], f["download_url"]) for f in resp.json() if f["name"].lower().endswith(".pdf")]
    log.info("Found %d PDFs in repo", len(pdfs))
    pdfs = [(name, url) for name, url in pdfs if re.search(args.match, name)]
    if args.limit:
        pdfs = pdfs[: args.limit]
    log.info("Downloading %d PDFs (match=%r, limit=%d)", len(pdfs), args.match, args.limit)

    downloaded, skipped, failed = 0, 0, []
    for i, (name, url) in enumerate(pdfs, start=1):
        dest = f"{pdf_dir}/{name}"
        if os.path.exists(dest) and os.path.getsize(dest) > 0:
            skipped += 1
            log.debug("[%d/%d] skip (exists) %s", i, len(pdfs), name)
            continue
        try:
            r = requests.get(url, timeout=120)
            r.raise_for_status()
            with open(dest, "wb") as f:
                f.write(r.content)
            downloaded += 1
            log.info("[%d/%d] downloaded %s (%.1f MB)", i, len(pdfs), name, len(r.content) / 1e6)
        except Exception as e:  # keep going, report at the end
            failed.append((name, str(e)))
            log.error("[%d/%d] FAILED %s: %s", i, len(pdfs), name, e)

    log.info("Done: downloaded=%d skipped=%d failed=%d", downloaded, skipped, len(failed))
    if failed:
        raise RuntimeError(f"{len(failed)} downloads failed: {[n for n, _ in failed]}")


if __name__ == "__main__":
    main()
