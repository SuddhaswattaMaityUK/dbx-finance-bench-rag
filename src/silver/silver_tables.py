"""The silver tables and views."""


def create_silver_tables(spark, n):
    """Create the silver schema, tables and views if they do not exist. Safe to run again, so every task can call it."""
    spark.sql(f"CREATE SCHEMA IF NOT EXISTS {n.catalog}.{n.silver_schema}")
    spark.sql(f"CREATE VOLUME IF NOT EXISTS {n.catalog}.{n.silver_schema}.checkpoints")  # the stream's checkpoint
    spark.sql(f"""
    CREATE TABLE IF NOT EXISTS {n.parsed} (
      path STRING, part_no INT, page_offset INT, parsed VARIANT, pdf_pages INT, pages INT, parsed_at TIMESTAMP
    )""")
    spark.sql(f"""
    CREATE TABLE IF NOT EXISTS {n.pages} (
      path STRING, page_no INT, markdown STRING, converted_at TIMESTAMP
    )""")
    spark.sql(f"""
    CREATE TABLE IF NOT EXISTS {n.log} (
      path STRING, stage STRING, page_no INT, attempt INT, retryable BOOLEAN, reason STRING, pdf_pages INT, logged_at TIMESTAMP,
      part_no INT
    )""")

    # One Markdown document per PDF, only when all its parts are parsed and all its pages are converted. The page
    # markers and the separator between pages are added here, so the model never has to write them.
    spark.sql(f"""
    CREATE OR REPLACE VIEW {n.documents} AS
    SELECT p.path, g.markdown, p.pages
    FROM (SELECT path, count(*) AS n FROM {n.parts} GROUP BY path) t
    JOIN (SELECT path, count(*) AS n, sum(pages) AS pages FROM {n.parsed} GROUP BY path) p ON p.path = t.path AND p.n = t.n
    JOIN (
      SELECT path, count(*) AS n,
             concat_ws('\\n\\n---\\n\\n', transform(array_sort(collect_list(struct(page_no, concat('<!-- page ', page_no, ' -->\\n', markdown)))), x -> x.col2)) AS markdown
      FROM {n.pages} GROUP BY path
    ) g ON g.path = p.path AND g.n = p.pages
    """)

    # What is still open: a parse failure until its part is parsed, a page failure until the page is converted.
    spark.sql(f"""
    CREATE OR REPLACE VIEW {n.failures} AS
    SELECT l.path, l.stage, l.part_no, l.page_no, max(l.attempt) AS attempts,
           max_by(l.retryable, l.attempt) AS retryable, max_by(l.reason, l.attempt) AS reason, max(l.pdf_pages) AS pdf_pages
    FROM {n.log} l
    LEFT JOIN {n.parsed} p ON l.stage = 'parse' AND p.path = l.path AND p.part_no = l.part_no
    LEFT JOIN {n.pages} g ON l.stage = 'convert' AND g.path = l.path AND g.page_no = l.page_no
    WHERE p.path IS NULL AND g.path IS NULL AND (l.stage = 'convert' OR l.part_no IS NOT NULL)
    GROUP BY l.path, l.stage, l.part_no, l.page_no
    """)
