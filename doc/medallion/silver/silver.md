# Ingestion, part 3: Silver layer

The `silver_parser` task runs after [bronze](../bronze/bronze.md) and converts the PDFs to Markdown. Code: [src/silver_pdfs.ipynb](../../../src/silver_pdfs.ipynb).

```
bronze_pdfs --ai_parse_document--> silver_pdfs.parsed --ai_query--> silver_pdfs.markdown
```

One table, `silver_pdfs` (`path`, `parsed` VARIANT, `markdown`, `parts` MAP<INT,STRING>, `num_parts`), filled in two notebook cells:

1. `ai_parse_document` parses each new PDF into `parsed`.
2. `ai_query` converts each document in parts of `pages_per_call` pages, so every call stays under the endpoint's 10000-token output cap. Finished parts are stored in `parts`, so a rerun only redoes missing parts. When all parts exist, `markdown` is built from them in order.
   The prompt keeps all content, titles (`#`), headings (`##`), plain text, tables (Markdown tables), metadata (page headers/footers) and puts `---` plus `<!-- page N -->` between pages.

Each step only processes PDFs not yet processed. The `endpoint` parameter (default `databricks-qwen3-next-80b-a3b-instruct`) selects the model. Billed per use, so test on a few PDFs first. To rebuild, drop `silver_pdfs` and rerun.
