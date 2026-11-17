"""Parse PDF parts, check the result, and file it: complete parses to silver_parsed, the others to silver_log."""

import json

from pyspark.sql import functions as F

from checks import check_parse, content_pages
from names import insert_new


def parse_docs(spark, n, df):
    """Parse the parts in `df` (columns path, part_no, page_offset, content). Returns (number stored, number logged as bad)."""
    # One pass over the parts: the parse is billed, so it must not run twice. The batch is small, so the
    # parsed JSON is collected and checked in Python.
    rows = df.select(
        "path", "part_no", "page_offset", F.expr("CAST(ai_parse_document(content, map('version', '2.0')) AS STRING)").alias("json")
    ).collect()
    attempts = {
        (r.path, r.part_no): r.n
        for r in spark.table(n.log).filter("stage = 'parse'").groupBy("path", "part_no").agg(F.max("attempt").alias("n")).collect()
    }

    good, bad = [], []
    for r in rows:
        doc = json.loads(r.json)
        pdf_pages = len(doc["document"]["pages"])
        problem = check_parse(doc)
        if problem is None:
            good.append((r.path, r.part_no, r.page_offset, r.json, pdf_pages, content_pages(doc)))
        else:
            reason, retryable = problem
            bad.append((r.path, "parse", None, attempts.get((r.path, r.part_no), 0) + 1, retryable, reason[:500], pdf_pages, r.part_no))

    if good:
        parsed = spark.createDataFrame(good, "path string, part_no int, page_offset int, j string, pdf_pages int, pages int").select(
            "path", "part_no", "page_offset", F.expr("parse_json(j)").alias("parsed"), "pdf_pages", "pages", F.current_timestamp().alias("parsed_at")
        )
        insert_new(spark, parsed, n.parsed, ["path", "part_no"])
    if bad:
        logged = spark.createDataFrame(
            bad, "path string, stage string, page_no int, attempt int, retryable boolean, reason string, pdf_pages int, part_no int"
        ).withColumn("logged_at", F.current_timestamp())
        insert_new(spark, logged, n.log, ["path", "part_no", "stage", "page_no", "attempt"])
    return len(good), len(bad)
