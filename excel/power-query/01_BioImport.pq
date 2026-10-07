let
    Source = Excel.CurrentWorkbook(){[Name="tblBioSource"]}[Content],
    Typed = Table.TransformColumnTypes(Source, {{"SEQN", Int64.Type}} & List.Transform(List.RemoveItems(Table.ColumnNames(Source), {"SEQN"}), each {_, type number}))
in
    Typed
