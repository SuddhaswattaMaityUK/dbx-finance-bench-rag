# Moving to one schema per layer (one-off)

Before, one schema (`finance_bench_rag`) held the volume, bronze and silver. Now bronze and silver have a schema each:

| | Schema | Holds |
| --- | --- | --- |
| Bronze | `finance_bench_bronze` | The volume, `bronze_pdfs`, `bronze_pdf_parts` |
| Silver | `finance_bench_silver` | `silver_parsed`, `silver_pages`, `silver_log`, the views and the checkpoint volume |

Dev has the same pair with a `_dev` suffix (the old dev schema was `finance_bench_rag_dev`).

## What moves, and what does not

- **Copied** (the work was paid for): `silver_parts` (now `bronze_pdf_parts`), `silver_parsed`, `silver_pages` and `silver_log`.
- **Rebuilt for free:** the volume and `bronze_pdfs`. The `download` task fetches the PDFs again and Auto Loader reloads them.
- **The `path` is rewritten.** It is the full volume path and includes the schema, so every copied `path` is changed to the new volume. Without it no key would match and everything would be parsed again.

## Steps (per target)

1. Wait until no ingest run is active, so the old tables are not changing.
2. Deploy the new version (merge to `master` for prod, any push for dev).
3. Run the one-off job **before** the pipeline: `databricks bundle run migrate_to_layer_schemas -t <target>`. It creates the schemas and tables, copies the four tables if the new ones are empty, and fails if a count differs.
4. Run the pipeline: `databricks bundle run financebench_pipeline -t <target>`. It downloads the PDFs into the new volume, loads bronze, finds that every PDF already has parts and parses nothing that was parsed.
5. Run `validate_silver`. The counts in `silver_documents` must be what they were before.
6. Drop the old schema when you are sure (`DROP SCHEMA workspace.finance_bench_rag CASCADE`). This cannot be undone.
7. Delete `resources/migrate_job.yml`, `src/migrate/`, the `old_schema` variable and this page.

Running the pipeline first (step 4 before step 3) would cut and parse every PDF again. The job guards nothing against that, so keep the order.
