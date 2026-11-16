# dbx-finance-bench-rag

A RAG pipeline on Databricks over the [FinanceBench](https://github.com/patronus-ai/financebench) filings. It is integrated with CI/CD: pushing a branch deploys the Databricks Asset Bundle to `dev`, and merging to `main` deploys it to `prod` (see [doc/setup.md](doc/setup.md#4-cicd-with-github-actions)).

## Download

The `ingest_financebench` job downloads all FinanceBench PDFs into a Unity Catalog volume (`/Volumes/<catalog>/<schema>/docs/pdfs/`). It is safe to rerun: files already in the volume are skipped.

![PDFs dumped into the volume](doc/download/PDF_DUMPS.png)

Details: [doc/download/download.md](doc/download/download.md)

## Bronze

The `bronze_pdfs` task of the `ingest_financebench` job loads the downloaded PDFs, as is, into the Delta table `bronze_pdfs`. Silver and gold come later. Details are in the notebook itself: [src/bronze_pdfs.ipynb](src/bronze_pdfs.ipynb)

## Documentation

| Doc | Contents |
| --- | --- |
| [doc/setup.md](doc/setup.md) | CLI install, authentication, deploying the bundle, CI/CD, GitHub secrets, Unity Catalog grants |
| [doc/download/download.md](doc/download/download.md) | How the PDF download works |
