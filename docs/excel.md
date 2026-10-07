# Excel use and native completion

Open `excel/NHANES_Native_Excel.xlsx` for the copy tested in desktop Excel. The original authored `excel/NHANES_Dashboard.xlsx` is also retained. The yellow biomarker selector changes age/sex medians and their chart. Formula summaries use the AdultsSnapshot table; GroupResults holds the independently reconciled grouped snapshot. Source sheets are typed, prepared extracts; original XPT files remain in `data/raw`.

The supplied workbook contains tables, formulas and charts. Power Query, PivotTables and slicers are supplied as automation instructions and have not yet been installed or verified. The script route returned access denied. Power Query opened through app control, but editor text input did not succeed. Dashboard native calculation and save/reopen checks did succeed.

## Completion script

Use Windows desktop Excel and run `powershell -NoProfile -File .\excel\Complete-Excel.ps1` from the repository root. The script creates a separate `NHANES_Rebuilt_Excel.xlsx`, refuses to overwrite an existing output, installs six M queries, compares loaded outputs to the CSVs, creates two PivotTables and two shared slicers, and saves/reopens the result. Inspect the status in `reports/excel_native_validation.json`.

The missingness PivotTable averages IsMissing, which is 0/1, by biomarker. The observed-means PivotTable uses one biomarker page filter to avoid mixing units. Sex and age slicers connect to both PivotTables. After script success, click slicer selections and check both tables, then restore the intended view. Do not describe interactive filtering as verified merely because the script has created slicers.

## Manual fallback

If local policy prevents the script from running, Excel's Data → Get Data → From Other Sources → Blank Query opens the Power Query editor. In Advanced Editor, paste the six numbered files in order. Name each query BioImport, DemoImport, Joined, Adults, LongMeasurements and Missingness respectively. The first two queries read the existing tblBioSource and tblDemoSource workbook tables. Load the remaining queries to new worksheet tables.

Compare row counts and missing slots with `reports/validation.json`; examine a sample of IDs and all grouped missing counts. Make PivotTables from LongMeasurements, using Biomarker on rows and IsMissing averaged as a percentage. For means, use AgeBand rows, SexLabel columns, Value averaged and a single Biomarker filter. Insert age and sex slicers and use Report Connections to link both PivotTables. Manual work does not automatically create a machine validation record; document the checks actually performed.

The Python pipeline rebuilds processed data, SQLite, reports and figures. It does not rewrite the committed dashboard. This version is pinned to the original 2017–2018 files. Extending to other cycles or biomarkers requires updating the workbook source tables, query mappings, formulas, cohort rules and checks together.
