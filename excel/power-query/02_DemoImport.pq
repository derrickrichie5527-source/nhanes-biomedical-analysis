let
    Source = Excel.CurrentWorkbook(){[Name="tblDemoSource"]}[Content],
    Typed = Table.TransformColumnTypes(Source, {{"SEQN", Int64.Type}, {"RIDAGEYR", Int64.Type}, {"RIAGENDR", Int64.Type}, {"WTMEC2YR", type number}, {"SDMVSTRA", Int64.Type}, {"SDMVPSU", Int64.Type}})
in
    Typed
