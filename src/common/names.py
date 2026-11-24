"""Names of the tables, views and paths of the layers, and the write helper every notebook shares.

Bronze, silver and gold have a schema each, so each layer can be granted, dropped or rebuilt on its own.
"""

from dataclasses import dataclass

from delta.tables import DeltaTable


@dataclass(frozen=True)
class Names:
    catalog: str
    bronze_schema: str
    silver_schema: str
    gold_schema: str = ""  # only the gold and retrieval notebooks pass it

    def _gold(self, name):
        assert self.gold_schema, "Names(...) was built without a gold_schema"
        return f"{self.catalog}.{self.gold_schema}.{name}"

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

    # silver: parsed parts, the log of failed parses and the view of what is still open
    @property
    def parsed(self):
        return self._silver("silver_parsed")

    @property
    def log(self):
        return self._silver("silver_log")

    @property
    def failures(self):
        return self._silver("silver_failures")

    # gold: the chunks (children are searched, parents are read by the LLM) and the retrieval test results
    @property
    def children(self):
        return self._gold("gold_children")

    @property
    def parents(self):
        return self._gold("gold_parents")

    @property
    def retrieval_results(self):
        return self._gold("test_retrieval_results")

    @property
    def tiktoken_cache(self):
        return f"/Volumes/{self.catalog}/{self.gold_schema}/cache/tiktoken"

    @property
    def vector_index(self):
        return self._gold("gold_children_index")


def insert_new(spark, df, table, keys):
    """Insert the rows whose key is not in the table yet. Running it twice with the same rows changes nothing."""
    condition = " AND ".join(f"t.{k} <=> s.{k}" for k in keys)
    DeltaTable.forName(spark, table).alias("t").merge(df.alias("s"), condition).whenNotMatchedInsertAll().execute()
