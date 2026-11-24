"""The gold tables."""

CHILD_COLUMNS = """
  chunk_id STRING NOT NULL, strategy STRING NOT NULL, parent_id STRING, chunk_no INT,
  path STRING NOT NULL, company STRING, fiscal_period STRING, doc_type STRING,
  chunk_type STRING, heading_path STRING, page_start INT, page_end INT,
  text STRING, embed_text STRING, parent_text STRING, n_tokens INT"""

PARENT_COLUMNS = """
  parent_id STRING NOT NULL, parent_no INT,
  path STRING NOT NULL, company STRING, fiscal_period STRING, doc_type STRING,
  chunk_type STRING, heading_path STRING, page_start INT, page_end INT,
  text STRING, n_tokens INT"""


def create_gold_tables(spark, n):
    """Create the gold schema, tables and the tiktoken cache volume if they do not exist. Safe to run again."""
    spark.sql(f"CREATE SCHEMA IF NOT EXISTS {n.catalog}.{n.gold_schema}")
    spark.sql(f"CREATE VOLUME IF NOT EXISTS {n.catalog}.{n.gold_schema}.cache")  # tiktoken's vocabulary

    # What is searched: structured children and fixed chunks. `embedding` is filled by embed_chunks, once per chunk.
    # Change Data Feed is how a Delta Sync index sees new, changed and deleted rows.
    spark.sql(f"""
    CREATE TABLE IF NOT EXISTS {n.children} ({CHILD_COLUMNS},
      embedding ARRAY<FLOAT>, chunked_at TIMESTAMP
    ) TBLPROPERTIES (delta.enableChangeDataFeed = true)""")

    # What the LLM reads for structured: whole sections (up to parent_tokens) and whole tables.
    spark.sql(f"CREATE TABLE IF NOT EXISTS {n.parents} ({PARENT_COLUMNS}, chunked_at TIMESTAMP)")

    # One row per test_retrieval run, strategy, search mode and k.
    spark.sql(f"""
    CREATE TABLE IF NOT EXISTS {n.retrieval_results} (
      run_at TIMESTAMP, strategy STRING, search STRING, k INT, questions INT,
      doc_hit DOUBLE, page_hit DOUBLE, evidence_hit DOUBLE, mrr DOUBLE
    )""")
