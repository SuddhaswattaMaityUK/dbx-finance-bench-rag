# Silver layer: operations

The design, the stages and the challenges are in the [README](../../../README.md#3-silver-pdfs-to-markdown), and every stage is explained in its notebook in [src/silver/](../../../src/silver/). This page is for **running and looking after** the silver layer.

## What is where

| Name | Kind | Holds |
| --- | --- | --- |
| `silver_parsed` | table | One row per PDF with a complete parse (`path`, `parsed` VARIANT, `pdf_pages`, `pages`, `parsed_at`) |
| `silver_pages` | table | The Markdown of each converted page (`path`, `page_no`, `markdown`, `converted_at`) |
| `silver_log` | table | The trail of every failure (`path`, `stage` parse or convert, `page_no`, `attempt`, `retryable`, `reason`, `pdf_pages`, `logged_at`) |
| `silver_documents` | view | The final Markdown per PDF, only when all its pages are converted |
| `silver_failures` | view | What is still open: PDFs not parsed and pages not converted, with the last reason |

`page_no` is the real PDF page number. The `<!-- page N -->` markers in `silver_documents` use the same number.

## Where to look

```sql
-- How much is done
SELECT (SELECT count(*) FROM silver_parsed)    AS pdfs_parsed,
       (SELECT count(*) FROM silver_documents) AS documents_complete,
       (SELECT count(*) FROM silver_pages)     AS pages_converted;

-- What is still open, and why
SELECT stage, retryable, count(*) FROM silver_failures GROUP BY stage, retryable;
SELECT * FROM silver_failures ORDER BY stage, path;

-- The history of one PDF
SELECT * FROM silver_log WHERE path LIKE '%PEPSICO_2018%' ORDER BY logged_at;
```

## What to do when something is open

| In `silver_failures` | Meaning | What to do |
| --- | --- | --- |
| stage `parse`, retryable | Pages failed (rate limit, internal error) | Run the job. The retry takes it, within `retry_page_budget`. After `max_attempts` it is left alone: raise `max_attempts` for one run if you want another try |
| stage `parse`, not retryable | A PDF over 500 pages, or a failed conversion | A retry cannot help. Split the PDF into smaller files, or accept that it is missing |
| stage `convert` | A page returned an error or an empty answer | Run the job. The page is tried again, up to `max_attempts` |
| nothing, but a PDF is not in `silver_documents` | Pages are not converted yet (the budget stopped the run) | Run the job again |

## Running it with a small quota

Every stage has a budget, so one run cannot spend more than you set:

| Widget | Limits |
| --- | --- |
| `retry_page_budget` | PDF pages parsed again in one run. `0` = no retries |
| `max_pages_per_run` | Pages converted with `ai_query` in one run. `0` = no conversion |
| `max_files_per_batch` | PDFs parsed at once by the stream (small = fewer rate-limit errors) |
| `max_attempts` | Tries per PDF or page before giving up |

A good first run on a new set of PDFs: `retry_page_budget` 0 and `max_pages_per_run` 100. Look at the result with the queries above, then raise the budgets.

## Maintenance notes

- Every stage only does what is missing. Running the job twice in a row does nothing the second time.
- `silver_log` only grows. A failure is never deleted: it stops being listed in `silver_failures` when the PDF or page is finally stored.
- To redo the Markdown with a new prompt: `DELETE FROM silver_pages`, then run. The parses are kept.
- Full rebuild: drop the three tables and two views, delete the checkpoint folder `/Volumes/<catalog>/<schema>/docs/_checkpoints/silver_parse`, and run.
- **Tasks.** `silver_parse` (stream: parse and check), `silver_retry` (parse the retryable failures again, within a budget) and `silver_convert` (one `ai_query` call per page). Each one creates the tables if they are missing, so each can be run alone.
- **Validation is a separate job.** `validate_silver` only reads the tables and fails if a rule that must hold is broken (a PDF with no record, duplicate or empty pages, pages beyond the document). Run it after the ingest job: `databricks bundle run validate_silver -t <target>`.
- **Where the logic lives.** Checks on parser and model output: `src/silver/checks.py` (plain Python, tested with `pytest`). Table and view definitions and the insert helper: `src/silver/tables.py`. Parse and file a PDF: `src/silver/parsing.py`.
- The first version of silver used one table, `silver_pdfs`, with a parts map. Its work was moved into the new tables without calling the parser or the model again. It is no longer used.
