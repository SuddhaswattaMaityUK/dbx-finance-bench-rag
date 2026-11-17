# Silver layer: happy and unhappy paths

What the silver stages do in each case. How to look after what stays open, and the flowchart of what is retryable and what is not, are in [silver.md](silver.md#silver_log-retryable-and-not-retryable).

## Happy path

| Case | What happens |
| --- | --- |
| First run | PDFs over `part_pages` pages are cut into parts. The stream parses every part (two files at a time). Complete parses go to `silver_parsed`. Every page of them is converted into `silver_pages`. The `silver_documents` view shows the PDFs whose pages are all there |
| Rerun, nothing new | The stream skips recorded parts, there is nothing to retry, no page is missing. Nothing is spent |
| A new PDF arrives | Download and bronze add it. The stream parses it, and its pages are converted |
| A run stops early (the service keeps failing) | The next run continues with the pages that are still missing |

## Unhappy paths

| Case | What happens | What to do |
| --- | --- | --- |
| The parser fails some pages (rate limit, internal error) | The parse of that part is incomplete, so it is **not** stored. It goes to `silver_log` as retryable. The retry parses the part again later (one at a time, at most `part_pages` pages). The other parts of the PDF are kept | Nothing. Run the job. See `silver_failures` |
| The parser rejects a part (failed conversion) | Logged as not retryable | Accept it is missing |
| `ai_query` returns an error or an empty answer for a page | The page is logged and tried again on the next run, up to `max_attempts` | Nothing, or lower the load |
| The model writes a page marker or `---` | The code removes them. The view adds the real ones | Nothing |
| The job fails in the middle of the parse stream | The checkpoint did not move past the failed micro-batch. The next run restarts there and skips the parts already recorded, so nothing is parsed twice | Run the job again |
| The job fails while converting pages | Pages are saved in chunks of 200. At most one chunk is lost, and only its missing pages are converted next time | Run the job again |
| The service keeps rate-limiting | Two failed retries in a row stop the retries for that run | Wait and run again, or lower `max_files_per_batch` |
| A PDF is deleted from the volume | Nothing happens. Bronze and silver keep their rows (silver is an archive) | Nothing |
| A PDF is re-uploaded with changed content (same name) | Ignored. Bronze tracks files by path, so the new version is never loaded | To support it: `cloudFiles.allowOverwrites` in bronze, and key the silver tables by path and modification time |
| A row is deleted from `bronze_pdfs` | Silver keeps its rows. The stream also fails on the delete | Add `skipChangeCommits` to the stream's read if you expect deletes |

## Decisions left open

- [ ] Support re-uploaded PDFs, or leave as is?
- [ ] Follow deletes from bronze, or keep silver as an archive?
- [x] Split the PDFs over 500 pages so they can be parsed: done, every PDF over `part_pages` pages is cut into parts.
