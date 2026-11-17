"""The bronze table of PDF parts."""


def create_parts_table(spark, n):
    """Create the table of PDF parts if it does not exist. Safe to run again."""
    spark.sql(f"""
    CREATE TABLE IF NOT EXISTS {n.parts} (
      path STRING, part_no INT, page_offset INT, pages INT, content BINARY, split_at TIMESTAMP
    )""")
