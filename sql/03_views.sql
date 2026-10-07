-- Independent SQL transformations for reconciliation with the pipeline.
CREATE VIEW v_joined AS
 SELECT b.*,d.RIDAGEYR,d.RIAGENDR,d.WTMEC2YR,d.SDMVSTRA,d.SDMVPSU
 FROM nhanes_bio b LEFT JOIN nhanes_demo d ON b.SEQN=d.SEQN;

CREATE VIEW v_adults AS
 WITH cohort AS (SELECT * FROM v_joined WHERE RIDAGEYR>=20)
 SELECT *, CASE RIAGENDR WHEN 1 THEN 'Male' WHEN 2 THEN 'Female' ELSE 'Unknown' END AS SexLabel,
 CASE WHEN RIDAGEYR<40 THEN '20-39' WHEN RIDAGEYR<60 THEN '40-59'
      WHEN RIDAGEYR<80 THEN '60-79' ELSE '80+' END AS AgeBand
 FROM cohort;

CREATE VIEW v_long AS
 WITH unpivoted AS (
 SELECT SEQN,'ALT' AS Biomarker,LBXSATSI AS Value,'U/L' AS Unit FROM v_adults
 UNION ALL SELECT SEQN,'AST',LBXSASSI,'U/L' FROM v_adults
 UNION ALL SELECT SEQN,'GGT',LBXSGTSI,'IU/L' FROM v_adults
 UNION ALL SELECT SEQN,'Albumin',LBXSAL,'g/dL' FROM v_adults
 UNION ALL SELECT SEQN,'Creatinine',LBXSCR,'mg/dL' FROM v_adults
 UNION ALL SELECT SEQN,'BUN',LBXSBU,'mg/dL' FROM v_adults
 )
 SELECT u.*,a.SexLabel,a.AgeBand,
 CASE WHEN u.Value IS NULL THEN 1 ELSE 0 END AS IsMissing
 FROM unpivoted u JOIN v_adults a ON u.SEQN=a.SEQN;

CREATE VIEW v_missingness AS
 SELECT Biomarker,Unit,SexLabel,AgeBand,COUNT(*) AS Participants,
 COUNT(Value) AS Observed,SUM(IsMissing) AS Missing,
 1.0*SUM(IsMissing)/COUNT(*) AS MissingRate
 FROM v_long GROUP BY Biomarker,Unit,SexLabel,AgeBand;

-- Window functions provide exact group medians without an extension.
CREATE VIEW v_grouped_stats AS
 WITH ranked AS (
 SELECT *,ROW_NUMBER() OVER(PARTITION BY Biomarker,Unit,SexLabel,AgeBand ORDER BY Value,SEQN) AS rn,
 COUNT(*) OVER(PARTITION BY Biomarker,Unit,SexLabel,AgeBand) AS n
 FROM v_long WHERE Value IS NOT NULL
 ), medians AS (
 SELECT Biomarker,Unit,SexLabel,AgeBand,AVG(Value) AS Median
 FROM ranked WHERE rn IN ((n+1)/2,(n+2)/2)
 GROUP BY Biomarker,Unit,SexLabel,AgeBand
 ), basic AS (
 SELECT Biomarker,Unit,SexLabel,AgeBand,COUNT(*) AS Participants,COUNT(Value) AS Observed,
 SUM(IsMissing) AS Missing,AVG(Value) AS Mean,MIN(Value) AS Minimum,MAX(Value) AS Maximum
 FROM v_long GROUP BY Biomarker,Unit,SexLabel,AgeBand
 )
 SELECT b.*,m.Median,1.0*b.Missing/b.Participants AS MissingRate
 FROM basic b LEFT JOIN medians m
 ON b.Biomarker=m.Biomarker AND b.Unit=m.Unit AND b.SexLabel=m.SexLabel AND b.AgeBand=m.AgeBand;
