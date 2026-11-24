# Silver layer: happy and unhappy paths

What the silver stages do in each case. How to look after what stays open, and the flowchart of what is retryable and what is not, are in [silver.md](silver.md#silver_log-retryable-and-not-retryable).

## Happy path

| Case | What happens |
| --- | --- |
| First run | PDFs over `part_pages` pages are cut into parts. `silver_parse` parses every part (two PDFs at a time). Complete parses go to `silver_parsed`. Gold chunks the PDFs whose parts are all there |
| Rerun, nothing new | No part is missing and nothing is retryable. Nothing is spent |
| A new PDF arrives | Download and bronze add it. The next run parses it |
| A run stops early (the service keeps failing) | The next run continues with the parts that are still missing |

## Unhappy paths

| Case | What happens | What to do |
| --- | --- | --- |
| The parser fails some pages (rate limit, internal error) | The parse of that part is incomplete, so it is **not** stored. It goes to `silver_log` as retryable. The next run parses the part again (at most `part_pages` pages, up to `max_attempts` times). The other parts of the PDF are kept | Nothing. Run the job. See `silver_failures` |
| The parser rejects a part (failed conversion) | Logged as not retryable | Accept it is missing |
| The job fails in the middle of the parse | Every batch is saved before the next one. The next run parses only the parts that are still missing, so nothing is parsed twice | Run the job again |
| The service keeps rate-limiting | Two batches in a row that store nothing stop the run | Wait and run again, or lower `pdfs_per_batch` |
| A PDF is deleted from the volume | Nothing happens. Bronze and silver keep their rows (silver is an archive) | Nothing |
| A PDF is re-uploaded with changed content (same name) | Ignored. Bronze tracks files by path, so the new version is never loaded | To support it: `cloudFiles.allowOverwrites` in bronze, and key the silver tables by path and modification time |
| A row is deleted from `bronze_pdfs` | Silver keeps its rows. Nothing else happens: the parse reads what is missing, not a change feed | Nothing |

## Decisions left open

- [ ] Support re-uploaded PDFs, or leave as is?
- [ ] Follow deletes from bronze, or keep silver as an archive?
- [x] Split the PDFs over 500 pages so they can be parsed: done, every PDF over `part_pages` pages is cut into parts.
