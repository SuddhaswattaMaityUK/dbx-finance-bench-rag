# dbx-finance-bench-rag

A RAG pipeline on Databricks over the [FinanceBench](https://github.com/patronus-ai/financebench) filings. It is integrated with CI/CD: pushing a branch deploys the Databricks Asset Bundle to `dev`, and merging to `main` deploys it to `prod` (see [doc/setup.md](doc/setup.md#4-cicd-with-github-actions)).

## Ingestion

The `ingest_financebench` job downloads all FinanceBench PDFs into a Unity Catalog volume (`/Volumes/<catalog>/<schema>/docs/pdfs/`). It is safe to rerun: files already in the volume are skipped.

![PDFs dumped into the volume](doc/ingestion/PDF_DUMPS.png)

Details: [doc/ingestion/ingest_raw.md](doc/ingestion/ingest_raw.md)

## Documentation

| Doc | Contents |
| --- | --- |
| [doc/setup.md](doc/setup.md) | CLI install, authentication, deploying the bundle, CI/CD, GitHub secrets, Unity Catalog grants |
| [doc/ingestion/ingest_raw.md](doc/ingestion/ingest_raw.md) | How the raw PDF ingestion works |
