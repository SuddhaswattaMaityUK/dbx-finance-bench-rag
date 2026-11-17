# Ingestion, part 2: Bronze layer

This is the second task, `bronze_pdfs`, of the `ingest_financebench` job. It runs after [part 1, download](../../download/download.md) and loads the PDFs from the volume into the Delta table `bronze_pdfs`, as is. Nothing is parsed or transformed. Silver (parsed plain text) and gold (chunked text) come later.

```
download  -->  /Volumes/<catalog>/<schema>/docs/pdfs/*.pdf  -->  bronze_pdfs
```

![Job run: download then bronze_pdfs, both succeeded](bronze_graph.png)

The code and a step-by-step explanation are in the notebook [src/ingest/bronze_pdfs.ipynb](../../../src/ingest/bronze_pdfs.ipynb). The task is defined in [resources/ingest_job.yml](../../../resources/ingest_job.yml) and receives `catalog` and `schema` from the bundle variables in [databricks.yml](../../../databricks.yml).

## Table

| Column | Meaning |
| --- | --- |
| `path` | Full volume path |
| `modificationTime` | File modification time |
| `length` | File size in bytes |
| `content` | Raw PDF bytes |

![bronze_pdfs table in Catalog Explorer](bronze_table_created_by_autoloader.png)

## How it loads

The load is incremental. It uses [Auto Loader](https://docs.databricks.com/aws/en/ingestion/cloud-object-storage/auto-loader/) (`cloudFiles`, `binaryFile` format) with `trigger(availableNow=True)`, so each run loads only the PDFs it has not seen, appends them and stops. Auto Loader records processed files in a checkpoint at `/Volumes/<catalog>/<schema>/docs/_checkpoints/bronze_pdfs`.

The first run, shown in the job graph above, read and wrote 368 rows, one per PDF, in about 50 seconds on serverless compute.

## Running it

```bash
databricks bundle deploy -t dev
databricks bundle run ingest_financebench -t dev
```

## Requirements

The service principal needs the Unity Catalog grants listed in [setup.md](../../setup.md#one-time-setup), plus write access to the volume.

## Notes

- Files are tracked by path, so a PDF that changes upstream under the same name is not reloaded.
- To rebuild from scratch, drop `bronze_pdfs`, delete the checkpoint folder and rerun. Dropping only the table leaves the checkpoint, so nothing would be reloaded.
- No file arrival trigger is needed. The `download` task writes the PDFs in the same job run.
