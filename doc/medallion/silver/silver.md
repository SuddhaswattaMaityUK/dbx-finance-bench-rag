# Ingestion, part 3: Silver layer

The `silver_parser` task runs after [bronze](../bronze/bronze.md) and converts the PDFs to Markdown. Code: [src/silver_pdfs.ipynb](../../../src/silver_pdfs.ipynb).

```
bronze_pdfs --ai_parse_document--> silver_pdfs.parsed --ai_query--> silver_pdfs.markdown
```

One table, `silver_pdfs` (`path`, `parsed` VARIANT, `markdown`), filled in two notebook cells:

1. `ai_parse_document` parses each new PDF into `parsed`.
2. `ai_query` fills `markdown` where it is empty. The prompt keeps all content, titles (`#`), headings (`##`), plain text, tables (Markdown tables), metadata (page headers/footers) and puts `---` plus `<!-- page N -->` between pages.

Each step only processes PDFs not yet processed. The `endpoint` parameter (default `databricks-claude-sonnet-4`) selects the model. Billed per use, so test on a few PDFs first. To rebuild, drop `silver_pdfs` and rerun.
