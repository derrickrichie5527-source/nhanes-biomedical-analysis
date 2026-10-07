# Verification record

Local verification date: 7 October 2026.

- Source hashes matched the pinned original CDC downloads.
- All 6,401 laboratory IDs matched exactly one demographics row.
- The adult cohort contains 5,265 unique IDs and 31,590 unique long keys.
- Missing slots: 2,111; observed measurements: 29,479. No imputation or outlier removal.
- CSVs were read back and compared with their prepared source frames.
- SQLite integrity returned `ok`; foreign-key violations: zero.
- Independently constructed SQL views matched every long-form record and all 48 group summaries.
- Six regression tests passed using the real source files.
- Excel formula summary counts/medians matched the overall summary in the authoring engine. Changing the selector to Creatinine changed group medians; ALT was restored before export.
- Dashboard and source-table previews, plus all three PDF pages, were visually reviewed.

Machine-readable evidence: `reports/validation.json`, `reports/sql_reconciliation.csv`, `reports/excel_artifact_validation.json`; test evidence: `reports/test_results.txt`.

## Pending checks

Desktop Excel COM activation failed with E_ACCESSDENIED (80070005) in the authoring environment. Consequently, the completion script has not been executed, and its Power Query refresh, PivotTables and slicers are unverified. The supplied dashboard remains a populated workbook snapshot. Desktop app control did open the workbook, force full calculation, save and reopen it. Formula results for all six biomarker summaries and 16 age/sex cells matched the independent CSV summaries with ALT and Creatinine selected. Two charts persisted. All 20,975 records across the five source/group/log sheets matched the CSVs, preserving blanks; no cached formula errors were found. ALT was restored for review. The query editor opened, but text input through app control did not reach its M editor, so query refresh remains unverified.

The completion script creates a separate native workbook and records pass/failure in `reports/excel_native_validation.json`. It compares query outputs with CSV data, saves and reopens the workbook, and checks feature counts. Even after script success, manually exercise slicer filters and confirm that both PivotTables respond. A report file merely existing is not evidence of a pass; inspect its status.

The [first GitHub Actions run](https://github.com/derrickrichie5527-source/nhanes-biomedical-analysis/actions/runs/37650890215) passed on 7 October 2026: the pipeline, six regression tests, saved workbook checks and output upload all succeeded. See the Actions page for the latest result.

Additional evidence: `reports/excel_native_alt_checks.json`, `reports/excel_native_creatinine_checks.json`, `reports/excel_ui_verification.json`, `reports/excel_automation_attempt.json` and `reports/reproduction_validation.json`. The latter confirms a pipeline run from a fresh ZIP extraction and byte-identical reproduction of all nine CSVs.
