# Desktop browser observations — 2026-09-10

Local uvicorn at127.0.0.1:8017, Codex in-app browser, standard GUI actions. Synthetic data only. Accessibility-tree observations, not screenshot-based visual review.

Verified:
- Demo loads three rows, one invalid and two without detected errors.
- Identifier0012 retained,1234.50 decimal,2026-09-10 date,9000duration seconds,approved status displayed.
- Invalid0013 remains visible with separate amount/date/duration/status errors.
- Setting amount mapping to Non associé immediately hides old results/exports and prompts recalculation. Reapplying retains three rows and leaves optional amounts empty.
- Setting required id mapping to Non associé produces three invalid rows, each with Required value missing.
- Editing schema clears mappings and stale results.
- Malformed JSON previously exposed raw English parser text. Fixed to show a clear French correction message; reloaded browser confirmed it.
- Clicking the synthetic example after malformed schema restores valid rules and3rows/1invalid output.
- JSON/CSV export buttons clicked; CSV request returned200 in local server logs. Saved download files were not located, so end-to-end downloaded contents are NOT verified.

Limitations: native file chooser was clicked but file selection not completed; native Codex app access is unavailable through the computer-use tool. Do not claim uploaded-file GUI acceptance. No mobile, keyboard-only, screenshot visual, actual client dataset or public deployment acceptance. Engine/API tests cover multipart files and exports separately.
