"""Table and view names, their definitions, and the one write helper the silver notebooks share."""

from dataclasses import dataclass

from delta.tables import DeltaTable


@dataclass(frozen=True)
class Names:
    catalog: str
    schema: str

    def _t(self, name):
        return f"{self.catalog}.{self.schema}.{name}"

    @property
    def bronze(self):
        return self._t("bronze_pdfs")

    @property
    def parsed(self):
        return self._t("silver_parsed")

    @property
    def pages(self):
        return self._t("silver_pages")

    @property
    def log(self):
        return self._t("silver_log")

    @property
    def documents(self):
        return self._t("silver_documents")

    @property
    def failures(self):
        return self._t("silver_failures")

    @property
    def parse_checkpoint(self):
        return f"/Volumes/{self.catalog}/{self.schema}/docs/_checkpoints/silver_parse"


def create_tables(spark, n):
    """Create the silver tables and views if they do not exist. Safe to run again, so every task can call it."""
    spark.sql(f"""
    CREATE TABLE IF NOT EXISTS {n.parsed} (
      path STRING, parsed VARIANT, pdf_pages INT, pages INT, parsed_at TIMESTAMP
    )""")
    spark.sql(f"""
    CREATE TABLE IF NOT EXISTS {n.pages} (
      path STRING, page_no INT, markdown STRING, converted_at TIMESTAMP
    )""")
    spark.sql(f"""
    CREATE TABLE IF NOT EXISTS {n.log} (
      path STRING, stage STRING, page_no INT, attempt INT, retryable BOOLEAN, reason STRING, pdf_pages INT, logged_at TIMESTAMP
    )""")

    # One Markdown document per PDF, only when all its pages are converted. The page markers and the
    # separator between pages are added here, so the model never has to write them.
    spark.sql(f"""
    CREATE OR REPLACE VIEW {n.documents} AS
    SELECT p.path, g.markdown, p.pages
    FROM {n.parsed} p
    JOIN (
      SELECT path, count(*) AS n,
             concat_ws('\\n\\n---\\n\\n', transform(array_sort(collect_list(struct(page_no, concat('<!-- page ', page_no, ' -->\\n', markdown)))), x -> x.col2)) AS markdown
      FROM {n.pages} GROUP BY path
    ) g ON g.path = p.path AND g.n = p.pages
    """)

    # What is still open: a parse failure until the PDF is parsed, a page failure until the page is converted.
    spark.sql(f"""
    CREATE OR REPLACE VIEW {n.failures} AS
    SELECT l.path, l.stage, l.page_no, max(l.attempt) AS attempts,
           max_by(l.retryable, l.attempt) AS retryable, max_by(l.reason, l.attempt) AS reason, max(l.pdf_pages) AS pdf_pages
    FROM {n.log} l
    LEFT JOIN {n.parsed} p ON l.stage = 'parse' AND p.path = l.path
    LEFT JOIN {n.pages} g ON l.stage = 'convert' AND g.path = l.path AND g.page_no = l.page_no
    WHERE p.path IS NULL AND g.path IS NULL
    GROUP BY l.path, l.stage, l.page_no
    """)


def insert_new(spark, df, table, keys):
    """Insert the rows whose key is not in the table yet. Running it twice with the same rows changes nothing."""
    condition = " AND ".join(f"t.{k} <=> s.{k}" for k in keys)
    DeltaTable.forName(spark, table).alias("t").merge(df.alias("s"), condition).whenNotMatchedInsertAll().execute()
