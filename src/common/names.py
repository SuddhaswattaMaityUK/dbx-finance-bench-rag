"""Names of the tables, views and paths of the two layers, and the write helper every notebook shares.

Bronze and silver have a schema each, so each layer can be granted, dropped or rebuilt on its own.
"""

from dataclasses import dataclass

from delta.tables import DeltaTable


@dataclass(frozen=True)
class Names:
    catalog: str
    bronze_schema: str
    silver_schema: str

    def _bronze(self, name):
        return f"{self.catalog}.{self.bronze_schema}.{name}"

    def _silver(self, name):
        return f"{self.catalog}.{self.silver_schema}.{name}"

    # bronze: the raw PDFs, whole and cut into parts
    @property
    def volume(self):
        return f"/Volumes/{self.catalog}/{self.bronze_schema}/docs"

    @property
    def bronze(self):
        return self._bronze("bronze_pdfs")

    @property
    def parts(self):
        return self._bronze("bronze_pdf_parts")

    # silver: parsed parts, converted pages, the log and the two views
    @property
    def parsed(self):
        return self._silver("silver_parsed")

    @property
    def pages(self):
        return self._silver("silver_pages")

    @property
    def log(self):
        return self._silver("silver_log")

    @property
    def documents(self):
        return self._silver("silver_documents")

    @property
    def failures(self):
        return self._silver("silver_failures")

    @property
    def parse_checkpoint(self):
        return f"/Volumes/{self.catalog}/{self.silver_schema}/checkpoints/parse"


def insert_new(spark, df, table, keys):
    """Insert the rows whose key is not in the table yet. Running it twice with the same rows changes nothing."""
    condition = " AND ".join(f"t.{k} <=> s.{k}" for k in keys)
    DeltaTable.forName(spark, table).alias("t").merge(df.alias("s"), condition).whenNotMatchedInsertAll().execute()
