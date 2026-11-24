"""The silver tables and the failures view."""


def create_silver_tables(spark, n):
    """Create the silver schema, tables and view if they do not exist. Safe to run again, so every task can call it."""
    spark.sql(f"CREATE SCHEMA IF NOT EXISTS {n.catalog}.{n.silver_schema}")
    spark.sql(f"""
    CREATE TABLE IF NOT EXISTS {n.parsed} (
      path STRING, part_no INT, page_offset INT, parsed VARIANT, pdf_pages INT, pages INT, parsed_at TIMESTAMP
    )""")
    spark.sql(f"""
    CREATE TABLE IF NOT EXISTS {n.log} (
      path STRING, stage STRING, page_no INT, attempt INT, retryable BOOLEAN, reason STRING, pdf_pages INT, logged_at TIMESTAMP,
      part_no INT
    )""")

    # What is still open: a parse failure until its part is parsed. `stage` and `page_no` are kept so the view and the
    # log keep their columns: every failure is a parse failure now (silver no longer converts pages, so page_no is empty).
    spark.sql(f"""
    CREATE OR REPLACE VIEW {n.failures} AS
    SELECT l.path, l.stage, l.part_no, l.page_no, max(l.attempt) AS attempts,
           max_by(l.retryable, l.attempt) AS retryable, max_by(l.reason, l.attempt) AS reason, max(l.pdf_pages) AS pdf_pages
    FROM {n.log} l
    LEFT JOIN {n.parsed} p ON p.path = l.path AND p.part_no = l.part_no
    WHERE l.stage = 'parse' AND l.part_no IS NOT NULL AND p.path IS NULL
    GROUP BY l.path, l.stage, l.part_no, l.page_no
    """)
