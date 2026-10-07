# Methodology

## Question and cohort

Study availability and descriptive distributions of ALT, AST, GGT, Albumin, Creatinine and BUN in the NHANES 2017–2018 adult biochemistry sample. Select age 20+ after joining demographics to laboratory records on SEQN. The biochemistry file has 6,401 records; all match demographics. The adult restriction retains 5,265 and excludes 1,136. Demographics has 9,254 records; participants without a biochemistry record are outside this laboratory-led cohort.

## Source fidelity and cleaning

Original XPT files are retained byte for byte. SHA-256 hashes are checked before processing. Selected source columns have explicit numeric/code types. Missingness remains missing; no clinical threshold, imputation or outlier deletion is applied.

The SAS transport decoder represents some exact zeros as nonzero values around 5.4e-79. Correct nonzero values with absolute magnitude below 1e-70 only in LBDSATLC, LBDSGTLC, RIDAGEYR and WTMEC2YR. This restores documented code/age/weight zeros. Do not apply the rule to biomarker measurements. The cleaning log records the affected counts. The source CSVs and workbook source tabs are therefore prepared extracts, not byte-identical raw data.

Use recorded sex codes 1/2 to label Male/Female and age bands 20–39, 40–59, 60–79 and 80+. Source age is top-coded at 80. Preserve ALT/GGT detection-limit flags in the wide data and applicable long records. Retain original source measurement units.

## Join and reshape

Require unique, nonmissing integer SEQN values in each source. Use a one-to-one laboratory-led left join and reject unmatched laboratory IDs. One adult must yield exactly six rows in long format, even when some measurements are missing. The long key is (SEQN, Biomarker). Six times 5,265 yields 31,590 slots; 29,479 values are observed and 2,111 are missing.

Power Query creates explicit measurement records rather than using a null-dropping unpivot. SQL uses UNION ALL. CSV round trips compare loaded values to the prepared frames, preserving identifier/code types. The CSVs retain analysis values but do not promise preservation of every SAS special-missing tag or file-level metadata; consult the original XPT and codebooks for those details.

## Summaries and review flags

Group by biomarker, recorded sex and age band: 6 × 2 × 4 = 48 groups. Participants counts include missing slots; Observed and Missing partition Participants. Means, medians, minima and maxima exclude missing measurements. MissingRate = Missing / Participants. Never average measurements across biomarkers with different units.

Calculate pooled adult Q1/Q3 separately per biomarker using the pipeline's default linear quantiles. Flag observed values outside Q1 − 1.5 IQR or Q3 + 1.5 IQR; preserve null flags for missing measurements. There are 1,457 flagged measurement values, not necessarily 1,457 distinct participants. This statistical review rule does not classify clinical abnormality, diagnose disease or justify removing observations. No flagged observation is removed.

## Independent verification

SQLite views independently join source tables, restrict adults and reconstruct long data. A ROW_NUMBER/COUNT window calculation obtains group medians, including the two-middle-value average for even groups. Compare every long key and selected source/derived fields, then all 48 summary rows. SQLite integrity and foreign-key checks must pass. Excel COUNT, COUNTBLANK and MEDIAN summaries are checked against the independent overall summary; the selector is exercised with ALT and Creatinine.

Charts show units and demographic labels. Missingness bars include a zero baseline; the workbook uses a clearly labeled zero-valued plotting helper to anchor automatic scaling. The helper is a visualization control and is not a participant observation. The PDF uses a fixed 0–10% missingness scale.

## Limits

These are unweighted sample descriptions. NHANES uses a complex survey design; representative estimates and valid population uncertainty require appropriate weights, strata and PSU handling. WTMEC2YR, SDMVSTRA and SDMVPSU are retained but are not used in these summaries. Do not interpret the results as national prevalence, causal effects or clinical reference intervals. Eligibility, nonresponse and detection limits matter when extending the work.

Native Excel formula results, selector behavior, saving and reopening passed through desktop app control. Query refresh, PivotTables and slicers remain unverified: script activation was denied and app control could not enter M code in the editor reliably. The GitHub workflow passed on 7 October 2026, including the pipeline, six regression tests and saved workbook checks.
