# Browser verification — September 11, 2026

Verified against the local application at 127.0.0.1:8017 using synthetic data. These checks do not establish acceptance on a client dataset.

## Verified desktop behavior

- The built-in example loads three rows: two without detected errors and one invalid.
- Identifier 0012 retains its leading zeros; amount 1234.50, date 2026-09-10, duration 9000 seconds and approved status appear correctly.
- Invalid row 0013 remains visible with separate amount, date, duration and status errors.
- Changing a mapping clears stale results and exports. An unmapped required identifier produces errors on all rows; optional unmapped amounts remain empty after recalculation.
- Editing the schema clears stale mappings/results. Malformed JSON produces a French correction message; reloading the synthetic example recovers successfully.
- Native file selection of examples/synthetic.csv and examples/schema.json followed by analysis produces three rows with one invalid.
- The actual JSON and CSV download buttons saved files. Parsing those saved files confirmed all three rows, identifiers 0012/0013/0014, normalized values and all four errors on the invalid row. JSON also preserves raw source values.
- Full-page desktop screenshot visually inspected for readable mapping controls, normalized results and the highlighted invalid row. The screenshot uses the labelled built-in synthetic example.

[Actual desktop screenshot](browser-proof.png)

## Saved export checksums

SHA-256 of the downloaded synthetic example exports:

- JSON: ee299ac391314b5b42d1cf24e55799b4de30ddb43b2e24068ea723cc19180232
- CSV: cf0d068479d3aa0e1df9f13433c281e62e84a77ea740afccbf5713759da2d09b

## Remaining acceptance work

Native XLS/XLSX selection, narrow-screen layout and keyboard-only interaction remain unverified. Engine/API tests cover spreadsheet processing separately. Representative client files, agreed business rules, deployment requirements and final client acceptance are still needed.
