# dbx-finance-bench-rag

A RAG pipeline on Databricks over the [FinanceBench](https://github.com/patronus-ai/financebench) filings. It is integrated with CI/CD: pushing a branch deploys the Databricks Asset Bundle to `dev`, and merging to `master` deploys it to `prod` (see [doc/setup.md](doc/setup.md#4-cicd-with-github-actions)).

## Ingestion

The `ingest_financebench` job runs three tasks in order: download, bronze, then silver. Gold comes later.

![Job run: download then bronze_pdfs](doc/medallion/bronze/bronze_graph.png)

### Part 1: Download

The `download` task downloads all FinanceBench PDFs into a Unity Catalog volume (`/Volumes/<catalog>/<schema>/docs/pdfs/`). It is safe to rerun: files already in the volume are skipped.

![PDFs dumped into the volume](doc/download/PDF_DUMPS.png)

Details: [doc/download/download.md](doc/download/download.md)

### Part 2: Bronze layer

The `bronze_pdfs` task loads the downloaded PDFs, as is, into the Delta table `bronze_pdfs` with Auto Loader, so each run loads only new files. The first run loaded all 368 PDFs.

![bronze_pdfs table](doc/medallion/bronze/bronze_table_created_by_autoloader.png)

Details: [doc/medallion/bronze/bronze.md](doc/medallion/bronze/bronze.md)

### Part 3: Silver layer

The `silver_parser` task parses each PDF with `ai_parse_document`, then converts it to Markdown with `ai_query` (titles, headings, tables and page separators preserved) into the table `silver_pdfs`.

Details: [doc/medallion/silver/silver.md](doc/medallion/silver/silver.md)

## Documentation

| Doc | Contents |
| --- | --- |
| [doc/setup.md](doc/setup.md) | CLI install, authentication, deploying the bundle, CI/CD, GitHub secrets, Unity Catalog grants |
| [doc/download/download.md](doc/download/download.md) | Ingestion part 1: how the PDF download works |
| [doc/medallion/bronze/bronze.md](doc/medallion/bronze/bronze.md) | Ingestion part 2: the bronze table and the Auto Loader load |
| [doc/medallion/silver/silver.md](doc/medallion/silver/silver.md) | Ingestion part 3: parsing and Markdown conversion |
