-- Run these independently in SQLiteStudio after adding data/processed/nhanes.sqlite.
-- Unweighted sample descriptions: no clinical or population interpretation.
SELECT COUNT(*) AS adult_participants FROM v_adults;

SELECT Biomarker, COUNT(*) AS participant_slots,
       COUNT(Value) AS observed,
       SUM(CASE WHEN Value IS NULL THEN 1 ELSE 0 END) AS missing,
       ROUND(100.0 * SUM(CASE WHEN Value IS NULL THEN 1 ELSE 0 END) / COUNT(*), 2) AS missing_pct
FROM v_long GROUP BY Biomarker ORDER BY missing_pct DESC;

-- Use this existing window-derived view to inspect ALT medians with denominators.
SELECT Biomarker, Unit, SexLabel, AgeBand, Observed, Missing, Median
FROM v_grouped_stats WHERE Biomarker = 'ALT' ORDER BY AgeBand, SexLabel;

-- CTE: availability checks without discarding null measurement slots.
WITH availability AS (
    SELECT SEQN, COUNT(*) AS slots, COUNT(Value) AS observed
    FROM v_long GROUP BY SEQN
)
SELECT observed, COUNT(*) AS participants
FROM availability GROUP BY observed ORDER BY observed;
