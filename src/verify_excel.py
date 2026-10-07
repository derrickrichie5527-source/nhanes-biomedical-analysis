"""Check saved native review-workbook cells against CSVs; does not run Excel or refresh queries."""
from pathlib import Path
import csv, json, math, zipfile
import xml.etree.ElementTree as ET

root=Path(__file__).resolve().parents[1]
NS={'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
def cells(name):
    with zipfile.ZipFile(root/'excel/NHANES_Native_Excel.xlsx') as z:
        strings=[]
        if 'xl/sharedStrings.xml' in z.namelist():
            strings=[''.join(n.itertext()) for n in ET.fromstring(z.read('xl/sharedStrings.xml')).findall('s:si',NS)]
        data=ET.fromstring(z.read('xl/worksheets/'+name+'.xml'))
        values={}
        errors=[]
        formulas=0
        for c in data.findall('.//s:sheetData/s:row/s:c',NS):
            t=c.get('t'); value=c.find('s:v',NS)
            if c.find('s:f',NS) is not None: formulas+=1
            if t=='e': errors.append((c.get('r'),value.text if value is not None else ''))
            if t=='inlineStr': val=''.join(c.find('s:is',NS).itertext())
            elif value is None: val=None
            elif t=='s': val=strings[int(value.text)]
            elif t in ('str','b'): val=value.text
            else: val=float(value.text)
            values[c.get('r')]=val
        assert not errors, errors
        return values,formulas

dashboard, formula_count=cells('sheet1')
selector=dashboard['B4']
assert selector in ('ALT','Creatinine'),selector
assert dashboard['B6']==5265 and dashboard['E6']==2111
with (root/'data/processed/biomarker_summary.csv').open() as f:
    summary={r['Biomarker']:r for r in csv.DictReader(f)}
for row in range(10,16):
    expected=summary[dashboard['A'+str(row)]]
    for col,key in [('C','Observed'),('D','Missing'),('F','Median')]:
        assert math.isclose(dashboard[col+str(row)],float(expected[key]),rel_tol=1e-12)
with (root/'data/processed/missingness_by_group.csv').open() as f:
    groups={(r['Biomarker'],r['SexLabel'],r['AgeBand']):r for r in csv.DictReader(f)}
for row,band in enumerate(['20-39','40-59','60-79','80+'],19):
    for col,sex,key in [('B','Female','Median'),('C','Male','Median'),('D','Female','Observed'),('E','Male','Observed')]:
        assert math.isclose(dashboard[col+str(row)],float(groups[selector,sex,band][key]),rel_tol=1e-12)
assert dashboard['E4']==('U/L' if selector=='ALT' else 'mg/dL')
source_rows_checked=0
def col(number):
    result=''
    while number:
        number,rem=divmod(number-1,26)
        result=chr(65+rem)+result
    return result
for sheet,filename in [('sheet2','adults_wide.csv'),('sheet3','missingness_by_group.csv'),('sheet4','bio_source.csv'),('sheet5','demo_source.csv'),('sheet6','cleaning_log.csv')]:
    actual,_=cells(sheet)
    with (root/'data/processed'/filename).open() as f:
        reader=csv.reader(f)
        for row,record in enumerate(reader,1):
            for column,reference in enumerate(record,1):
                value=actual.get(col(column)+str(row))
                if reference=='': assert value is None or value=='',(sheet,row,column,value)
                elif isinstance(value,float): assert math.isclose(value,float(reference),rel_tol=1e-12,abs_tol=1e-12),(sheet,row,column,value,reference)
                else: assert value==reference,(sheet,row,column,value,reference)
            if row>1: source_rows_checked+=1
with zipfile.ZipFile(root/'excel/NHANES_Native_Excel.xlsx') as z:
    charts=[p for p in z.namelist() if p.startswith('xl/charts/chart') and p.endswith('.xml')]
    assert len(charts)==2
result={'saved_native_formula_values':'passed',
        'native_formula_summary_rows_verified':6,'native_group_formula_cells_verified':16,
        'selector_checked':selector,'cached_formula_errors':0,'charts_persisted':2,'source_rows_compared':source_rows_checked,
        'power_query_refresh':'pending: editor text input unavailable',
        'pivottables':'pending','slicers':'pending','automation_script':'failed: COM activation E_ACCESSDENIED'}
out=root/'reports'/('excel_native_'+selector.lower()+'_checks.json')
out.write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
