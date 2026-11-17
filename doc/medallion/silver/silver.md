# Silver layer: operations

The design, the stages and the challenges are in the [README](../../../README.md#3-silver-pdfs-to-markdown), and every stage is explained in its notebook in [src/silver/](../../../src/silver/). This page is for **running and looking after** the silver layer.

## What is where

| Name | Kind | Holds |
| --- | --- | --- |
| `silver_parts` | table | The PDFs cut into parts of at most `part_pages` pages (`path`, `part_no`, `page_offset`, `pages`, `content` bytes, `split_at`). A PDF with `part_pages` pages or fewer is one part |
| `silver_parsed` | table | One row per part with a complete parse (`path`, `part_no`, `page_offset`, `parsed` VARIANT, `pdf_pages`, `pages`, `parsed_at`) |
| `silver_pages` | table | The Markdown of each converted page (`path`, `page_no`, `markdown`, `converted_at`) |
| `silver_log` | table | The trail of every failure (`path`, `stage` parse or convert, `page_no`, `attempt`, `retryable`, `reason`, `pdf_pages`, `logged_at`, `part_no`). A parse failure is about a part (`part_no`), a convert failure about a page (`page_no`) |
| `silver_documents` | view | The final Markdown per PDF, only when all its parts are parsed and all its pages are converted |
| `silver_failures` | view | What is still open: parts not parsed and pages not converted, with the last reason |

`page_no` is the real PDF page number (the part's `page_offset` plus the parser's page id plus 1), also for a PDF cut into parts. The `<!-- page N -->` markers in `silver_documents` use the same number.

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
| stage `parse`, retryable | Pages of a part failed (rate limit, internal error) | Run the job. The retry takes the part (at most `part_pages` pages). After `max_attempts` it is left alone: raise `max_attempts` for one run if you want another try |
| stage `parse`, not retryable | A failed conversion | A retry cannot help. Accept that it is missing, or try other `part_pages` |
| stage `convert` | A page returned an error or an empty answer | Run the job. The page is tried again, up to `max_attempts` |
| nothing, but a PDF is not in `silver_documents` | Pages are not converted yet (a run stopped early) | Run the job again |

## Running it with a small quota

There are no budgets: a run does everything that is missing. The load is limited by:

| Widget | Limits |
| --- | --- |
| `max_files_per_batch` | PDFs parsed at once by the stream (small = fewer rate-limit errors) |
| `max_attempts` | Tries per PDF or page before giving up |

Two failed retries in a row stop the retries, and a convert chunk that stores nothing stops the conversion. Run again later.

## Maintenance notes

- Every stage only does what is missing. Running the job twice in a row does nothing the second time.
- `silver_log` only grows. A failure is never deleted: it stops being listed in `silver_failures` when the PDF or page is finally stored.
- To redo the Markdown with a new prompt: `DELETE FROM silver_pages`, then run. The parses are kept.
- Full rebuild: drop the four tables and two views, delete the checkpoint folder `/Volumes/<catalog>/<schema>/docs/_checkpoints/silver_parse_parts`, and run.
- **Tasks.** `silver_split` (cut long PDFs into parts), `silver_parse` (stream: parse and check), `silver_retry` (parse the retryable parts again) and `silver_convert` (one `ai_query` call per page). Each one creates the tables if they are missing, so each can be run alone.
- **One unit.** The job `financebench_pipeline` ([resources/financebench_pipeline_job.yml](../../../resources/financebench_pipeline_job.yml)) runs `ingest_financebench` and then `validate_silver`. Indexing will be added as a third task. Run it with `databricks bundle run financebench_pipeline -t <target>`.
- **Validation is a separate job.** `validate_silver` only reads the tables and fails if a rule that must hold is broken (a PDF with no record, duplicate or empty pages, pages beyond the document). Run it after the ingest job: `databricks bundle run validate_silver -t <target>`.
- **Where the logic lives.** Checks on parser and model output: `src/silver/checks.py` (plain Python, tested with `pytest`). Table and view definitions and the insert helper: `src/silver/tables.py`. Parse and file a PDF: `src/silver/parsing.py`.
- **Tables from before the split** had no part columns. Every task adds them when it runs (`create_tables`): an old parse becomes part 1 with offset 0, and old parse failures keep an empty `part_no`, so they are history and their PDFs are parsed again as parts.
- The first version of silver used one table, `silver_pdfs`, with a parts map. Its work was moved into the new tables without calling the parser or the model again. It is no longer used.
