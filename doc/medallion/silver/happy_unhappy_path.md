# Silver layer: happy and unhappy paths

Open questions and edge cases for the `silver_parser` task ([src/silver_pdfs.ipynb](../../../src/silver_pdfs.ipynb)). Nothing here is implemented yet unless marked **Done**. Pick it up from the "Decisions to make" list at the bottom.

How it works today:

```
bronze_pdfs --readStream + ai_parse_document (v2.0)--> silver_pdfs.parsed
silver_pdfs.parsed --ai_query + merge (update only)--> silver_pdfs.markdown
```

## Happy path

| Case | What happens |
| --- | --- |
| First run | Every bronze row is parsed and appended to `silver_pdfs`, then `markdown` is filled for all rows. |
| Rerun, nothing new | The checkpoint skips all bronze rows. Step 3 finds no rows with `markdown IS NULL`. Zero work. |
| New PDF arrives | Download and bronze add it. Step 2 parses only that row. Step 3 converts only that row. |

## Unhappy paths

### 1. A PDF is deleted from the volume

- **Today:** nothing happens. Bronze keeps its row, silver keeps its row.
- **Why:** Auto Loader only adds files and does not track deletes.
- **Verdict:** fine for a historical set like FinanceBench. Silver acts as an archive.

### 2. A row is deleted from `bronze_pdfs`

- **Today:** silver keeps its row. The step 2 stream also fails with a "data update or delete" error on the next run.
- **Fix to tolerate it:** add `.option("skipChangeCommits", "true")` to the `readStream` in step 2.
- **Fix to follow bronze:** add a cell after step 3:
  ```python
  spark.sql(f"DELETE FROM {silver} WHERE path NOT IN (SELECT path FROM {bronze})")
  ```

### 3. A PDF is re-uploaded with changed content (same name)

- **Today:** ignored. Bronze tracks files by path, so the new version is never loaded and silver keeps the old content.
- **Fix, if updates matter:**
  1. In bronze, set `cloudFiles.allowOverwrites` to `true`. The new version is appended with the same `path` and a newer `modificationTime`.
  2. Add `modificationTime` to `silver_pdfs` and treat `path` plus `modificationTime` as the key.
  3. Change the step 3 merge condition to `t.path = s.path AND t.modificationTime = s.modificationTime`. Without this, the merge matches two rows with the same path and fails.
  4. Optional cleanup: delete silver rows whose `modificationTime` is older than the newest one for that path.
- **Verdict:** not needed for FinanceBench, where the filings do not change.

### 4. `ai_parse_document` fails on a PDF

- **Today:** not handled. A failure stops the stream, so the task fails and nothing new is written for that batch.
- **To investigate:** whether v2.0 returns an error field inside the VARIANT instead of throwing. If so, store the error and skip the row in step 3.
- **Retry:** because the checkpoint only advances after a successful batch, a rerun retries the batch.

### 5. `ai_query` fails or is cut off

- **Today:** the merge fails, so no rows are updated in that run. Rows keep `markdown IS NULL` and are retried on the next run.
- **Risk:** `ai_query` is run with default error handling. A single bad document can fail the whole merge.
- **Fix to consider:** pass `failOnError => false`, keep the error message in a column, and update only the rows that succeeded.
- **Risk:** a very long filing can exceed the model's context window or `max_tokens` (32000). The output may be truncated without an error. Compare page counts against the number of `<!-- page N -->` markers to detect it.

### 6. The page separator is wrong

- **Why it can happen:** the model writes the `---` and `<!-- page N -->` lines itself, because each whole document goes in one call.
- **Check:** count `<!-- page N -->` markers per document and compare with the page count in `parsed`.
- **Alternative if it proves unreliable:** convert page by page and join the pages in code, so the separator is exact. This costs one call per page and more code.

### 7. Cost and runtime

- `ai_parse_document` and `ai_query` are billed per use. A first run over 368 filings can be large.
- **Mitigation:** test on a handful of PDFs first, for example by limiting rows read from `bronze_pdfs`, then run the full set.

### 8. Rebuild from scratch

Drop `silver_pdfs`, delete the checkpoint folder `/Volumes/<catalog>/<schema>/docs/_checkpoints/silver_pdfs`, then rerun. Dropping only the table leaves the checkpoint, so nothing would be reparsed.

To change only the prompt and keep the parsed output: `UPDATE silver_pdfs SET markdown = NULL`, then rerun step 3.

## Decisions to make

- [ ] Keep silver as an archive, or follow deletes from bronze (case 2)?
- [ ] Support re-uploaded PDFs (case 3), or leave as is?
- [ ] Handle `ai_parse_document` errors per row (case 4)?
- [ ] Use `failOnError => false` and store errors in `ai_query` (case 5)?
- [ ] Add a page-marker check after step 3, and switch to per-page conversion if it fails (case 6)?
