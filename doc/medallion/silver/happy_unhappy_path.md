# Silver layer: happy and unhappy paths

Open questions and edge cases for the `silver_parser` task ([src/silver_pdfs.ipynb](../../../src/silver_pdfs.ipynb)). Nothing here is implemented yet unless marked **Done**. Pick it up from the "Decisions to make" list at the bottom.

How it works today:

```
bronze_pdfs --readStream + ai_parse_document (v2.0)--> silver_pdfs.parsed
silver_pdfs.parsed --split into parts + ai_query--> silver_pdfs.parts --join--> silver_pdfs.markdown
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
- **Retry:** the checkpoint only advances after a successful batch, so a rerun retries that batch.

### 5. `ai_query` fails or is cut off

- **Done:** step 3 uses `failOnError => false` and stores only successful parts in `parts`. A document keeps `markdown` NULL until all its parts exist, and a rerun only redoes the missing parts. Work is saved per batch of `docs_per_batch` documents.
- **Done:** the output cap (10000 tokens) is handled by splitting into parts of `pages_per_call` pages.
- **Still open:** a part that always fails is retried in every batch. The loop stops when a batch stores nothing, but the errors are not saved. Consider an `errors` column to see why a part fails.
- **Still open:** a dense table page can exceed the cap on its own. Lower `pages_per_call` if parts keep failing.

### 6. The page separator is wrong

- **How it works:** the `---` between parts is added in code and is exact. Inside a part, the model writes `<!-- page N -->` and `---` between the pages.
- **Check:** count the `<!-- page N -->` markers per document and compare with the number of pages that have parsed content (dev run: they matched exactly for the three documents checked).
- **Note:** `ai_parse_document` can return no elements for some pages (blank or image-only), so the marker count can be lower than the PDF page count.

### 7. Cost and runtime

- `ai_parse_document` and `ai_query` are billed per use. A first run over 368 filings can be large.
- **Mitigation:** test on a handful of PDFs first, for example by limiting rows read from `bronze_pdfs`, then run the full set.

### 8. Rebuild from scratch

Drop `silver_pdfs`, delete the checkpoint folder `/Volumes/<catalog>/<schema>/docs/_checkpoints/silver_pdfs`, then rerun. Dropping only the table leaves the checkpoint, so nothing would be reparsed.

To change only the prompt and keep the parsed output: `UPDATE silver_pdfs SET markdown = NULL, parts = NULL, num_parts = NULL`, then rerun.

## Decisions to make

- [ ] Keep silver as an archive, or follow deletes from bronze (case 2)?
- [ ] Support re-uploaded PDFs (case 3), or leave as is?
- [ ] Handle `ai_parse_document` errors per row (case 4)?
- [ ] Store the `ai_query` error message per failed part (case 5)?
- [ ] Add a page-marker check after step 3 (case 6)?
