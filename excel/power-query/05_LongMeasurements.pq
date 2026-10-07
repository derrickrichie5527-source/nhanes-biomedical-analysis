let
    Source = Adults,
    Codes = {"LBXSATSI", "LBXSASSI", "LBXSGTSI", "LBXSAL", "LBXSCR", "LBXSBU"},
    Names = {"ALT", "AST", "GGT", "Albumin", "Creatinine", "BUN"},
    Units = {"U/L", "U/L", "IU/L", "g/dL", "mg/dL", "mg/dL"},
    AddMeasurements = Table.AddColumn(Source, "Measurements", (r) => List.Transform(List.Positions(Codes), (i) => [Biomarker = Names{i}, SourceVariable = Codes{i}, Value = Record.Field(r, Codes{i}), Unit = Units{i}, DetectionFlag = if i = 0 then r[LBDSATLC] else if i = 2 then r[LBDSGTLC] else null])),
    Keep = Table.SelectColumns(AddMeasurements, {"SEQN", "RIDAGEYR", "RIAGENDR", "SexLabel", "AgeBand", "WTMEC2YR", "SDMVSTRA", "SDMVPSU", "Measurements"}),
    ExpandList = Table.ExpandListColumn(Keep, "Measurements"),
    ExpandRecord = Table.ExpandRecordColumn(ExpandList, "Measurements", {"Biomarker", "SourceVariable", "Value", "Unit", "DetectionFlag"}),
    Typed = Table.TransformColumnTypes(ExpandRecord, {{"Value", type number}, {"DetectionFlag", Int64.Type}}),
    MissingFlag = Table.AddColumn(Typed, "IsMissing", each if [Value] = null then 1 else 0, Int64.Type)
in
    MissingFlag
