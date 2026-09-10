# Configurable Excel/CSV importer

An independent synthetic-data prototype for configurable spreadsheet imports. It has not been validated against a client dataset. The ingestion/normalization engine, CLI, local upload/mapping/preview interface and stateless API are implemented.23 automated tests pass. Browser interaction and visual QA remain unverified; buyer-specific acceptance is outstanding.

## Run

Python3.11+ intended; tested locally with Python3.14. Create an isolated environment:

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python importer.py examples/synthetic.csv examples/schema.json --output output.json
```

The sample is entirely synthetic. Expected:3rows,1invalid. JSON retains all rows and raw values, with field-level conversion errors and null normalized cells when invalid. Decimal quantities are strings to preserve decimal precision; duration output is seconds as a decimal string. Text identifiers retain source leading zeros. Numeric Excel formatting is not reconstructed: if Excel stores12 with a0000 display format, provide explicit identifier-width rules before expecting0012.

Use `--mapping mapping.json` to override target-to-source suggestions; every target must be present and unmapped values are null. Suggestions use deterministic accent/case/punctuation normalization and configured aliases. Ambiguous header matches remain unmapped. Missing required mappings generate errors for every data row. Blank rows are retained.

Use `--sheet Name` for multi-sheet workbooks; no silent first-sheet choice. CSV accepts comma, semicolon, tab or pipe. Pass `--delimiter ';'` if detection is ambiguous. Default encoding is strict UTF-8 with optional BOM; select `--encoding cp1252` explicitly for older exports. No replacement of undecodable bytes.

Schema examples cover text, decimal, date, duration and status. Dates are tried against explicitly listed formats; conflicting successful parses produce an error. Decimal/grouping separators are explicit; unknown currency strings are rejected rather than guessed. Status values are an explicit map. Durations use an explicit unit (`hours`, `minutes`, `seconds`, `hh:mm`). No business rules are inferred by an LLM. No runtime API keys or external calls.

## Local interface and API

```sh
.venv/bin/uvicorn api:app --host 127.0.0.1 --port 8017
```

Open http://127.0.0.1:8017/ locally. Select your file and load your project schema, or click the clearly labelled synthetic example. Inspect suggested column mappings, adjust dropdowns and apply. Review the first100rows and download all rows as JSON or CSV. Invalidating file/schema/options/mappings clears stale results. No public deployment or external accounts are involved. The HTML, CSS and JavaScript have no external assets. Static serving and JavaScript syntax were verified; actual browser interaction, mobile layout and keyboard flow have not yet been tested.

`POST /api/import` accepts multipart fields `file`, `schema` (JSON rule array), optional `mapping` (JSON target/source object), `sheet`, `encoding`, `delimiter`, `output` (`json` or `csv`). Add header `X-Importer-Client: local-ui`. JSON response includes source headers, suggested/applied mapping, notes, total/invalid counts and every source/normalized/error record. Default return is JSON. `GET /health` checks service availability. Each request contains its input; no upload IDs or retained file storage exist.

Request streams are bounded before multipart parsing; files are limited to10MiB and total request metadata adds256KiB. Rule text is limited to64KiB. Cross-origin requests are rejected, no CORS permission is granted, and response caching is disabled. The local client header is an anti-cross-site measure, **not authentication**. Do not bind to a public interface; a client deployment requires agreed authentication/network isolation and process resource limits. Multipart libraries may use temporary spooling during the request, closed afterward.

API tests include genuine multipart CSV/XLSX, mapping override, CSV download, source/field errors, malformed rule shapes, native Excel times, limits and origin/host rejection. Tests use FastAPI's in-process test client; there is no claim that network deployment or browser automation was tested. A test dependency emits an httpx deprecation warning; tests still pass.

## Formula handling and limits

XLSX formulas and spreadsheet error cells are preserved and flagged, without execution. Legacy XLS reader exposes cached formula values and cannot establish formula provenance: its warning is retained in results. Formula freshness is not verified. For provenance-sensitive imports, require a reviewed values-only export or an agreed alternative reader.

`export_csv(result)` retains every row plus source row number/error columns. It prefixes formula-like text with an apostrophe for spreadsheet safety; this changes the literal CSV representation, so the JSON is the canonical unmodified normalized representation. Raw source values remain in JSON, not CSV. Invalid rows are never silently discarded.

Input limits:10MiB,10000data rows,200columns. XLSX also limits ZIP entry count and advertised expanded bytes. These are basic bounds, not a full hostile-file sandbox. The CLI is local-only; do not expose it as a public file-upload service. No persistence beyond explicitly requested output; no analytics. For deployment add worker/process time and memory limits, isolation, and retention controls; the included API already limits the upload stream. Encrypted/password-protected workbooks are not supported. Merged/multirow/blank/duplicate headers require source cleanup or an agreed mapping enhancement.

## Remaining acceptance work

- Browser-level verification of upload → mapping → normalization → warnings/preview → complete downloads, including stale-state changes and narrow screens.
- Buyer target schema, representative XLS/XLSX/CSV files, expected mappings, dates/currencies/durations/status rules, volume and export preferences.
- Agreement on dataset confidentiality, deployment scope and final acceptance.
- Full integration tests on representative anonymized samples.

Reader references: [openpyxl workbook loading](https://openpyxl.readthedocs.io/en/stable/api/openpyxl.reader.excel.html), [xlrd API](https://xlrd.readthedocs.io/en/latest/api.html). No claim of security certification or complete buyer acceptance.
