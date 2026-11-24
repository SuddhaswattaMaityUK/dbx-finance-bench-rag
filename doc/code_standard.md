# Code standard

How code in this repository is written. Every new notebook or script follows it, and an old one is brought in line when it is rewritten.

## Notebooks

A notebook reads from top to bottom in this order of cells:

1. **Title (markdown).** What the notebook does, which task of which job runs it, and the table it writes, with its columns.
2. **Libraries (code, only if needed).** `%pip install ...` and then `dbutils.library.restartPython()`, each in its own cell.
3. **Imports (code).** Every import, and only imports, in one cell right after the libraries. No import appears further down.
4. **Constants (code).** Every name, path and setting, hardcoded, in `UPPER_CASE`. No widgets and no job parameters: to change a value, change the cell.
5. **Assets (code).** Creates what the notebook writes to: the catalog, schema, tables and volumes, each with `IF NOT EXISTS`, so a rerun changes nothing.
6. **Steps.** One markdown cell (`## Step n: ...`, what it does and why) followed by one code cell.
7. **Result (code).** A small query that shows what was written, such as a row count.

## No failure handling

Do not catch errors, retry, filter out failed rows or keep lists of what failed. If something fails, the task fails and the error is visible in the job run. Fix the cause and rerun. Every task is safe to rerun.

## Spark first

Do the work in Spark, so it runs in parallel on the executors and the data never goes through the driver.

1. **Built-in functions first** (`pyspark.sql.functions`, SQL functions such as `ai_parse_document`). They are the fastest.
2. **A UDF when Python is needed.** Prefer a pandas UDF (`@F.pandas_udf`) to a plain row-at-a-time `@F.udf`. Examples are splitting a PDF with `pypdf`, or chunking text with a library.
3. **Never** `collect()`, `toPandas()` or loop over rows in Python to transform data. Use them only to show a small result.

## Style

- Short code: one Spark chain per step, no helper functions for something used once.
- Comments only where the code does not explain itself, in plain English.
- Python follows PEP 8, with lines of up to 120 characters.
