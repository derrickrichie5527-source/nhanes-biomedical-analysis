<#
Creates a separate native Excel workbook from the committed dashboard.
Requires desktop Excel for Windows. No macros or SQLite ODBC driver are used.
The authoring session could not execute Excel COM. Native status stays pending
until this script refreshes, reconciles and saves successfully.
#>
[CmdletBinding()]
param([string]$OutputName = 'NHANES_Rebuilt_Excel.xlsx')
$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$baseFile = Join-Path $PSScriptRoot 'NHANES_Dashboard.xlsx'
if ([System.IO.Path]::GetFileName($OutputName) -ne $OutputName -or -not $OutputName.EndsWith('.xlsx')) {
    throw 'OutputName must be a filename ending in .xlsx.'
}
$outputFile = Join-Path $PSScriptRoot $OutputName
if (Test-Path -LiteralPath $outputFile) { throw 'Output already exists. Choose a new OutputName to preserve it.' }
$excelInstance = $null
$portfolioWorkbook = $null
$nativeStatus = @{ status = 'pending'; checks = @{} }
$missingArgument = [Type]::Missing

function Load-QueryTable([string]$QueryName, [string]$SheetName) {
    $sheet = $portfolioWorkbook.Worksheets.Add()
    $sheet.Name = $SheetName
    $connection = 'OLEDB;Provider=Microsoft.Mashup.OleDb.1;Data Source=$Workbook$;Location=' + $QueryName + ';Extended Properties=""'
    # xlSrcQuery=3, xlYes=1. Queries are available through the Mashup provider.
    $table = $sheet.ListObjects.Add(3, $connection, $missingArgument, 1, $sheet.Range('A1'))
    $table.Name = 'tblQuery' + $QueryName
    $table.QueryTable.CommandType = 2
    $table.QueryTable.CommandText = 'SELECT * FROM [' + $QueryName + ']'
    $table.QueryTable.BackgroundQuery = $false
    if (-not $table.QueryTable.Refresh($false)) { throw "Refresh cancelled: $QueryName" }
    if ($table.QueryTable.FetchedRowOverflow) { throw "Row overflow: $QueryName" }
    $table.TableStyle = 'TableStyleMedium2'
    $sheet.UsedRange.Columns.AutoFit() | Out-Null
    return $table
}

function Compare-QueryTable($Table, [string]$CsvName, [string[]]$Keys) {
    $expected = @(Import-Csv -LiteralPath (Join-Path $projectRoot ('data/processed/' + $CsvName)))
    if ($Table.ListRows.Count -ne $expected.Count) { throw "Row count mismatch: $CsvName" }
    $headers = $Table.HeaderRowRange.Value2
    $actual = $Table.DataBodyRange.Value2
    $columns = @{}
    for ($j=1; $j -le $Table.ListColumns.Count; $j++) { $columns[[string]$headers[1,$j]] = $j }
    $expectedMap = @{}
    foreach ($record in $expected) {
        $key = (($Keys | ForEach-Object { [string]$record.$_ }) -join '|')
        if ($expectedMap.ContainsKey($key)) { throw "Duplicate expected key: $key" }
        $expectedMap[$key] = $record
    }
    $seen = @{}
    for ($i=1; $i -le $expected.Count; $i++) {
        $key = (($Keys | ForEach-Object { [string]$actual[$i,$columns[$_]] }) -join '|')
        if (-not $expectedMap.ContainsKey($key) -or $seen.ContainsKey($key)) { throw "Missing/duplicated native key: $key" }
        $seen[$key] = $true
        $record = $expectedMap[$key]
        foreach ($name in $columns.Keys) {
            if (-not ($record.PSObject.Properties.Name -contains $name)) { continue }
            $value = $actual[$i,$columns[$name]]
            $reference = [string]$record.$name
            if ([string]::IsNullOrEmpty($reference)) {
                if ($null -ne $value -and [string]$value -ne '') { throw "Missing value changed: $key / $name" }
            } elseif ($value -is [double] -or $value -is [int]) {
                $target = [double]::Parse($reference, [Globalization.CultureInfo]::InvariantCulture)
                if ([Math]::Abs([double]$value-$target) -gt 1e-10*[Math]::Max(1,[Math]::Abs($target))) { throw "Numeric mismatch: $key / $name" }
            } elseif ([string]$value -ne $reference) { throw "Label mismatch: $key / $name" }
        }
    }
    return @{ rows_compared = $expected.Count; result = 'passed' }
}

try {
    $excelInstance = New-Object -ComObject Excel.Application
    $excelInstance.Visible = $false
    $excelInstance.DisplayAlerts = $false
    $excelInstance.AutomationSecurity = 3
    $portfolioWorkbook = $excelInstance.Workbooks.Open($baseFile, 0, $false)
    $names = @('BioImport','DemoImport','Joined','Adults','LongMeasurements','Missingness')
    $files = @(Get-ChildItem -LiteralPath (Join-Path $PSScriptRoot 'power-query') -Filter '*.pq' | Sort-Object Name)
    if ($files.Count -ne $names.Count) { throw 'Expected six Power Query files.' }
    for ($i=0; $i -lt $names.Count; $i++) {
        $formula = Get-Content -LiteralPath $files[$i].FullName -Raw
        $portfolioWorkbook.Queries.Add($names[$i],$formula,'NHANES reproducible preparation') | Out-Null
    }
    $joinedTable = Load-QueryTable 'Joined' 'QueryJoined'
    if ($joinedTable.ListRows.Count -ne 6401) { throw 'Native joined row count mismatch.' }
    $adultTable = Load-QueryTable 'Adults' 'Adults'
    $longTable = Load-QueryTable 'LongMeasurements' 'LongMeasurements'
    $missingTable = Load-QueryTable 'Missingness' 'Missingness'
    $nativeStatus.checks.adults = Compare-QueryTable $adultTable 'adults_wide.csv' @('SEQN')
    $nativeStatus.checks.long = Compare-QueryTable $longTable 'measurements_long.csv' @('SEQN','Biomarker')
    $nativeStatus.checks.missingness = Compare-QueryTable $missingTable 'missingness_by_group.csv' @('Biomarker','SexLabel','AgeBand')

    $pivotSheet = $portfolioWorkbook.Worksheets.Add()
    $pivotSheet.Name = 'PivotAnalysis'
    $pivotSheet.Range('A1').Value2 = 'Unweighted NHANES adult sample'
    $pivotSheet.Range('A2').Value2 = 'Missingness retains null slots. Means below use one selected biomarker.'
    $cache = $portfolioWorkbook.PivotCaches().Create(1, $longTable.Name)
    $missingPivot = $cache.CreatePivotTable($pivotSheet.Range('A5'),'ptMissingness')
    $missingPivot.PivotFields('Biomarker').Orientation = 1
    $missingPivot.AddDataField($missingPivot.PivotFields('IsMissing'),'Missing fraction',-4106).NumberFormat = '0.0%'
    $missingPivot.AddDataField($missingPivot.PivotFields('SEQN'),'Participant slots',-4112) | Out-Null
    $meanPivot = $cache.CreatePivotTable($pivotSheet.Range('A18'),'ptObservedMeans')
    $meanPivot.PivotFields('AgeBand').Orientation = 1
    $meanPivot.PivotFields('SexLabel').Orientation = 2
    $meanPivot.PivotFields('Biomarker').Orientation = 3
    $meanPivot.PivotFields('Biomarker').CurrentPage = 'ALT'
    $meanPivot.AddDataField($meanPivot.PivotFields('Value'),'Observed mean',-4106).NumberFormat = '0.00'
    $meanPivot.RowGrand = $false
    $meanPivot.ColumnGrand = $false
    $sexCache = $portfolioWorkbook.SlicerCaches.Add($missingPivot,'SexLabel','scSexLabel')
    $sexCache.PivotTables.AddPivotTable($meanPivot)
    $sexCache.Slicers.Add($pivotSheet,$missingArgument,'slSex','Recorded sex',50,520,140,125) | Out-Null
    $ageCache = $portfolioWorkbook.SlicerCaches.Add($missingPivot,'AgeBand','scAgeBand')
    $ageCache.PivotTables.AddPivotTable($meanPivot)
    $ageCache.Slicers.Add($pivotSheet,$missingArgument,'slAge','Age band',190,520,140,180) | Out-Null
    # No multi-biomarker slicer on the mean pivot: it must not mix units.
    $pivotSheet.UsedRange.Columns.AutoFit() | Out-Null
    foreach ($pivot in @($missingPivot,$meanPivot)) {
        if (-not $pivot.RefreshTable()) { throw 'Pivot refresh failed.' }
    }
    $nativeStatus.checks.pivots = @{ count=2; refresh='passed' }
    $nativeStatus.checks.slicers = @{ count=2; caches_created='passed'; interactive_filtering='not exercised' }
    $excelInstance.CalculateFull()
    $dashboardSheet = $portfolioWorkbook.Worksheets.Item('Dashboard')
    if ([int]$dashboardSheet.Range('B6').Value2 -ne 5265 -or [int]$dashboardSheet.Range('E6').Value2 -ne 2111) { throw 'Dashboard formula count mismatch.' }
    $dashboardSheet.Range('A33').Value2 = 'Native Power Query refresh and PivotTables passed. See native validation log.'
    $portfolioWorkbook.SaveAs($outputFile,51)
    $portfolioWorkbook.Close($false)
    $portfolioWorkbook = $null
    # Reopen the saved file and verify persistence, rather than only creation.
    $reopened = $excelInstance.Workbooks.Open($outputFile,0,$true)
    try {
        if ($reopened.Queries.Count -ne 6 -or $reopened.SlicerCaches.Count -ne 2) { throw 'Native features did not persist.' }
        if ($reopened.Worksheets.Item('LongMeasurements').ListObjects.Item(1).ListRows.Count -ne 31590) { throw 'Saved long-form count mismatch.' }
        $nativeStatus.checks.saved_workbook = 'passed'
    } finally { $reopened.Close($false) }
    $nativeStatus.status = 'passed'
    $nativeStatus.excel_version = $excelInstance.Version
    Write-Output ('Native Excel workbook verified: ' + $outputFile)
} catch {
    $nativeStatus.status = 'failed'
    $nativeStatus.error = $_.Exception.Message
    throw
} finally {
    if ($null -ne $portfolioWorkbook) { $portfolioWorkbook.Close($false) }
    if ($null -ne $excelInstance) {
        $excelInstance.Quit()
        [void][System.Runtime.InteropServices.Marshal]::FinalReleaseComObject($excelInstance)
    }
    $nativeStatus | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $projectRoot 'reports/excel_native_validation.json') -Encoding utf8
}
