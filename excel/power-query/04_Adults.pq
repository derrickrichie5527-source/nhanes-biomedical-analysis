let
    MinimumAge = 20,
    Source = Joined,
    Cohort = Table.SelectRows(Source, each [RIDAGEYR] <> null and [RIDAGEYR] >= MinimumAge),
    SexLabel = Table.AddColumn(Cohort, "SexLabel", each if [RIAGENDR] = 1 then "Male" else if [RIAGENDR] = 2 then "Female" else "Unknown", type text),
    AgeBand = Table.AddColumn(SexLabel, "AgeBand", each if [RIDAGEYR] < 40 then "20-39" else if [RIDAGEYR] < 60 then "40-59" else if [RIDAGEYR] < 80 then "60-79" else "80+", type text),
    ImportCodeFix = Table.TransformColumns(AgeBand, List.Transform({"LBDSATLC", "LBDSGTLC"}, (c) => {c, (v) => if v = null then null else if Number.Abs(v) < 1e-70 then 0 else v, type number}))
in
    ImportCodeFix
