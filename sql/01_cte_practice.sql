-- SQLite / SQLiteStudio CTE practice. Selected source CSVs are imported into
-- nhanes_bio and nhanes_demo using your database's import wizard.
-- Numeric blank CSV fields must become SQL NULL, not empty strings or zero.
-- SEQN is the participant key. Set integer types for IDs/codes, REAL or
-- DOUBLE PRECISION/FLOAT for laboratory values and WTMEC2YR.

-- 1. Check duplicates separately in both source tables.
SELECT SEQN, COUNT(*) AS records
FROM nhanes_bio
GROUP BY SEQN
HAVING COUNT(*) > 1;

SELECT SEQN, COUNT(*) AS records
FROM nhanes_demo
GROUP BY SEQN
HAVING COUNT(*) > 1;

-- 2. Verify every biochemistry participant matches demographics.
SELECT COUNT(*) AS unmatched
FROM nhanes_bio b
LEFT JOIN nhanes_demo d ON b.SEQN = d.SEQN
WHERE d.SEQN IS NULL;

-- 3. JOIN + adult cohort + readable labels using chained CTEs.
WITH joined AS (
    SELECT b.*, d.RIDAGEYR, d.RIAGENDR, d.WTMEC2YR, d.SDMVSTRA, d.SDMVPSU
    FROM nhanes_bio b
    LEFT JOIN nhanes_demo d ON b.SEQN = d.SEQN
), adults AS (
    SELECT * FROM joined WHERE RIDAGEYR >= 20
), labeled AS (
    SELECT *,
      CASE WHEN RIAGENDR = 1 THEN 'Male'
           WHEN RIAGENDR = 2 THEN 'Female' ELSE 'Unknown' END AS SexLabel,
      CASE WHEN RIDAGEYR < 40 THEN '20-39'
           WHEN RIDAGEYR < 60 THEN '40-59'
           WHEN RIDAGEYR < 80 THEN '60-79' ELSE '80+' END AS AgeBand
    FROM adults
)
SELECT SexLabel, AgeBand, COUNT(*) AS participants,
       COUNT(LBXSATSI) AS alt_observed,
       SUM(CASE WHEN LBXSATSI IS NULL THEN 1 ELSE 0 END) AS alt_missing,
       1.0 * SUM(CASE WHEN LBXSATSI IS NULL THEN 1 ELSE 0 END) / COUNT(*) AS alt_missing_rate
FROM labeled
GROUP BY SexLabel, AgeBand
ORDER BY SexLabel, AgeBand;
