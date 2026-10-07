# Explore the NHANES biomedical portfolio

This folder contains the source data, processed data, Excel workbooks, SQLite database, SQL, Power Query definitions, automation, reports, tests and GitHub workflow for this portfolio repository.

1. Read [README.md](README.md) for the project question, findings and scope.
2. Open [the native Excel review workbook](excel/NHANES_Native_Excel.xlsx). Its dashboard calculations were tested inside desktop Excel with ALT and Creatinine; ALT is restored. Power Query, PivotTables and slicers are **not installed in this copy**. Their completion remains pending.
3. Read [the PDF report](reports/NHANES_analysis.pdf).
4. Add [the database](data/processed/nhanes.sqlite) in SQLiteStudio and explore the SQL files.
5. Read [verification.md](docs/verification.md) and [GitHub handoff](docs/GITHUB_HANDOFF.md).

The clean original authored dashboard is also retained as NHANES_Dashboard.xlsx. The native copy preserves the same source records and formulas after desktop Excel recalculation and saving. A completion script is supplied for generating a separate NHANES_Rebuilt_Excel.xlsx with the pending features; its execution was blocked in this session.

Package checks include a successful pipeline run from an extracted copy, identical CSV reproduction, six regression tests, source hashes, independent SQL reconciliation, workbook source/value checks and document-link checks. Native Excel verification is partial, not complete. See the evidence files in reports.

The owner requested GitHub publication on 7 October 2026. Repository: [nhanes-biomedical-analysis](https://github.com/derrickrichie5527-source/nhanes-biomedical-analysis). Start with the files above; no additional dataset downloads are needed for review or the default pipeline run.
