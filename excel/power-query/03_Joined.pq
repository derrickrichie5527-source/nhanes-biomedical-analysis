let
    Bio = BioImport,
    Demo = DemoImport,
    ValidatedBio = if Table.RowCount(Bio) = List.Count(List.Distinct(Bio[SEQN])) and not List.Contains(Bio[SEQN], null) then Bio else error "Biochemistry keys are missing or duplicated",
    ValidatedDemo = if Table.RowCount(Demo) = List.Count(List.Distinct(Demo[SEQN])) and not List.Contains(Demo[SEQN], null) then Demo else error "Demographics keys are missing or duplicated",
    Merged = Table.NestedJoin(ValidatedBio, {"SEQN"}, ValidatedDemo, {"SEQN"}, "Demographics", JoinKind.LeftOuter),
    Checked = if List.AllTrue(List.Transform(Merged[Demographics], each Table.RowCount(_) = 1)) then Merged else error "Unmatched participant IDs",
    Expanded = Table.ExpandTableColumn(Checked, "Demographics", {"RIDAGEYR", "RIAGENDR", "WTMEC2YR", "SDMVSTRA", "SDMVPSU"})
in
    Expanded
