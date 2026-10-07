let
    Source = LongMeasurements,
    Grouped = Table.Group(Source, {"Biomarker", "SexLabel", "AgeBand"}, {{"Participants", each Table.RowCount(_), Int64.Type}, {"Missing", each List.Sum([IsMissing]), Int64.Type}, {"Observed", each List.NonNullCount([Value]), Int64.Type}}),
    MissingRate = Table.AddColumn(Grouped, "MissingRate", each [Missing] / [Participants], type number)
in
    MissingRate
