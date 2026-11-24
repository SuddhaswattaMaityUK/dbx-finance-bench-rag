# Ingestion, part 1: Download

This is the first task, `download`, of the `ingest_financebench` job. The next tasks load the PDFs into bronze and cut them into parts: [part 2, bronze layer](../medallion/bronze/bronze.md).

[src/bronze/download.py](../../src/bronze/download.py) downloads every PDF from the public
[patronus-ai/financebench](https://github.com/patronus-ai/financebench) `pdfs/` folder into a Unity Catalog volume.

## Flow

```mermaid
flowchart LR
    G["GitHub: patronus-ai/financebench<br/>pdfs/ folder"] -->|"one API call: list the PDFs"| L["List of 368 PDFs"]
    L -->|"--match and --limit<br/>(dev: a small sample)"| F["PDFs to fetch"]
    F --> E{"Already in the volume<br/>and not empty?"}
    E -- yes --> SK["skip"]
    E -- no --> D["download"]
    D -- ok --> V[("volume<br/>/Volumes/workspace/finance_bench_bronze/docs/pdfs/")]
    D -- failed --> FL["the task fails"]
    SK --> V
    V -.->|next task| B[bronze_pdfs]
```

## What it does

With `--match <regex>` and `--limit <n>` it downloads only a sample: the dev target uses `--match EARNINGS --limit 28` (28 short earnings releases) so that testing is cheap. Prod downloads all 368.

1. Creates the bronze schema and its `docs` volume if they don't exist (`IF NOT EXISTS`).
2. Lists the PDFs in the repo with one GitHub API call.
3. Downloads each PDF to `/Volumes/workspace/finance_bench_bronze/docs/pdfs/` (the constants at the top of the script).
4. Skips any file already in the volume, so reruns are cheap.
5. Logs each download as `[i/total] downloaded <name> (<size> MB)`. A failed download fails the task. Rerun it: the PDFs already downloaded are skipped.

## Idempotent reload

The load is idempotent: the script was rerun after the first pass had already downloaded everything. It found all 368 PDFs in the repo, skipped every one because it was already in the volume, and downloaded nothing. The run still succeeded.

## Running it

The job `ingest_financebench` is defined in [resources/ingest_job.yml](../../resources/ingest_job.yml). It runs on serverless compute and receives only `--match` and `--limit`, from the bundle variables `pdf_match` and `pdf_limit` in [databricks.yml](../../databricks.yml).

```bash
databricks bundle deploy -t dev
databricks bundle run ingest_financebench -t dev
```

## Next

The `bronze_pdfs` task runs after this one and loads the PDFs into a Delta table: [part 2, bronze layer](../medallion/bronze/bronze.md).

## Requirements

The service principal needs the Unity Catalog grants listed in [setup.md](../setup.md#one-time-setup).

## Notes

- Only the file name is checked, so a PDF that changes upstream is not re-downloaded.
- The GitHub API allows 60 unauthenticated calls per hour per IP. The job uses one.
