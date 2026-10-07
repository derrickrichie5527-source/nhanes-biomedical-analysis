"""Rebuild NHANES-derived data, SQLite results, figures and a PDF report."""
from pathlib import Path
import argparse
import hashlib
import json
import sqlite3
import urllib.request
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
BIO_URL = 'https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2017/DataFiles/BIOPRO_J'
DEMO_URL = 'https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2017/DataFiles/DEMO_J'
LABS = {
    'LBXSATSI': ('ALT', 'U/L'), 'LBXSASSI': ('AST', 'U/L'),
    'LBXSGTSI': ('GGT', 'IU/L'), 'LBXSAL': ('Albumin', 'g/dL'),
    'LBXSCR': ('Creatinine', 'mg/dL'), 'LBXSBU': ('BUN', 'mg/dL'),
}
BIO_FIELDS = ['SEQN', *LABS, 'LBDSATLC', 'LBDSGTLC']
DEMO_FIELDS = ['SEQN', 'RIDAGEYR', 'RIAGENDR', 'WTMEC2YR', 'SDMVSTRA', 'SDMVPSU']
EXPECTED_HASHES = {
    'BIOPRO_J.xpt': '5bcd5722c1892883b96a9d7fed0befadabacae313f800fadc0133cd5dd00c4c6',
    'DEMO_J.xpt': 'c0b46e0345ea19404928656277c8b0d10b0cca348a9b2fe4fc3c67e8b7ee73ec',
}

def get_sources(download=False):
    for name, expected in EXPECTED_HASHES.items():
        file = ROOT / 'data/raw' / name
        if download or not file.exists():
            base = BIO_URL if name.startswith('BIO') else DEMO_URL
            content = urllib.request.urlopen(base + '.xpt', timeout=60).read()
            if hashlib.sha256(content).hexdigest() != expected:
                raise ValueError('CDC source changed. Review the new source before replacing pinned data.')
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_bytes(content)
        if hashlib.sha256(file.read_bytes()).hexdigest() != expected:
            raise ValueError(f'Source integrity check failed: {name}')
    return (pd.read_sas(ROOT / 'data/raw/BIOPRO_J.xpt', format='xport'),
            pd.read_sas(ROOT / 'data/raw/DEMO_J.xpt', format='xport'))

def validate_keys(frame, name):
    if frame.SEQN.isna().any() or not frame.SEQN.is_unique:
        raise ValueError(f'{name}: missing or duplicated participant IDs')
    if not frame.SEQN.eq(frame.SEQN.round()).all():
        raise ValueError(f'{name}: non-integer participant IDs')

def prepare(bio, demo):
    validate_keys(bio, 'biochemistry')
    validate_keys(demo, 'demographics')
    source_bio, source_demo = bio[BIO_FIELDS].copy(), demo[DEMO_FIELDS].copy()
    logs = []
    # The source transport decoder represents some encoded zeros as ~5.4e-79.
    # Only code/weight fields are normalized; analyte measurements are untouched.
    for frame, columns in [(source_bio, ['LBDSATLC','LBDSGTLC']),
                           (source_demo, ['RIDAGEYR','WTMEC2YR'])]:
        for col in columns:
            mask = frame[col].notna() & (frame[col] != 0) & (frame[col].abs() < 1e-70)
            logs.append({'step':'Normalize transport zero','variable':col,
                         'affected_rows':int(mask.sum()),
                         'reason':'Decoder near-zero artifact in a source code/weight field; raw XPT retained'})
            frame.loc[mask, col] = 0
    for frame, columns in [(source_bio,['SEQN','LBDSATLC','LBDSGTLC']),
                           (source_demo,['SEQN','RIDAGEYR','RIAGENDR','SDMVSTRA','SDMVPSU'])]:
        for col in columns:
            if not frame[col].dropna().eq(frame[col].dropna().round()).all():
                raise ValueError(f'Unexpected non-integer code: {col}')
            frame[col] = frame[col].astype('Int64')
    for col in ['LBDSATLC','LBDSGTLC']:
        if not set(source_bio[col].dropna().tolist()) <= {0,1}:
            raise ValueError(f'Unexpected detection-limit code: {col}')
    if not set(source_demo.RIAGENDR.dropna().tolist()) <= {1,2}:
        raise ValueError('Unexpected source sex code')
    joined = source_bio.merge(source_demo, on='SEQN', how='left', validate='one_to_one', indicator=True)
    if not joined['_merge'].eq('both').all():
        raise ValueError('Unmatched biochemistry IDs')
    joined = joined.drop(columns='_merge')
    adults = joined.loc[joined.RIDAGEYR >= 20].copy()
    adults['SexLabel'] = adults.RIAGENDR.map({1:'Male',2:'Female'})
    adults['AgeBand'] = pd.cut(adults.RIDAGEYR, [19,39,59,79,200],
                              labels=['20-39','40-59','60-79','80+']).astype(str)
    logs.append({'step':'Select adult cohort','variable':'RIDAGEYR',
                 'affected_rows':len(joined)-len(adults), 'reason':'Age >= 20, predeclared exploratory adult cohort'})
    id_fields=['SEQN','RIDAGEYR','RIAGENDR','SexLabel','AgeBand','WTMEC2YR','SDMVSTRA','SDMVPSU']
    long = adults.melt(id_vars=id_fields, value_vars=list(LABS), var_name='SourceVariable', value_name='Value')
    long['Biomarker'] = long.SourceVariable.map({k:v[0] for k,v in LABS.items()})
    long['Unit'] = long.SourceVariable.map({k:v[1] for k,v in LABS.items()})
    long['DetectionFlag'] = pd.Series(pd.NA,index=long.index,dtype='Int64')
    for source, flag in [('LBXSATSI','LBDSATLC'),('LBXSGTSI','LBDSGTLC')]:
        mask=long.SourceVariable.eq(source)
        long.loc[mask,'DetectionFlag'] = long.loc[mask,'SEQN'].map(adults.set_index('SEQN')[flag])
    long['IsMissing'] = long.Value.isna().astype(int)
    long['IQRReviewFlag'] = pd.Series(pd.NA,index=long.index,dtype='Int64')
    bounds=[]
    for name, group in long.groupby('Biomarker',sort=True):
        observed=group.Value.dropna()
        q1,q3=observed.quantile([.25,.75]).tolist()
        lower,upper=q1-1.5*(q3-q1),q3+1.5*(q3-q1)
        idx=group.index[group.Value.notna()]
        long.loc[idx,'IQRReviewFlag']=((long.loc[idx,'Value']<lower)|(long.loc[idx,'Value']>upper)).astype(int)
        bounds.append({'Biomarker':name,'Unit':group.Unit.iloc[0],'Q1':q1,'Q3':q3,
                       'LowerFence':lower,'UpperFence':upper,'Flagged':int(long.loc[idx,'IQRReviewFlag'].sum())})
    logs.append({'step':'Flag for review','variable':'Six biomarkers','affected_rows':int(long.IQRReviewFlag.sum()),
                 'reason':'Pooled adult 1.5-IQR rule for statistical review only; no observations removed'})
    logs.append({'step':'Reshape wide to long','variable':'Six biomarkers','affected_rows':len(long),
                 'reason':'One row per participant and biomarker; all missing measurement slots retained'})
    long=long[['SEQN','RIDAGEYR','RIAGENDR','SexLabel','AgeBand','Biomarker','SourceVariable','Value','Unit',
               'DetectionFlag','IsMissing','IQRReviewFlag','WTMEC2YR','SDMVSTRA','SDMVPSU']]
    return source_bio, source_demo, joined, adults, long, pd.DataFrame(logs), pd.DataFrame(bounds)

def summaries(long):
    keys=['Biomarker','Unit','SexLabel','AgeBand']
    grouped=long.groupby(keys,dropna=False,sort=True)
    result=grouped.agg(Participants=('SEQN','size'),Observed=('Value','count'),
        Missing=('IsMissing','sum'),Median=('Value','median'),Mean=('Value','mean'),
        Minimum=('Value','min'),Maximum=('Value','max')).reset_index()
    result['MissingRate']=result.Missing/result.Participants
    overall=long.groupby(['Biomarker','Unit']).agg(Participants=('SEQN','size'),Observed=('Value','count'),
        Missing=('IsMissing','sum'),Median=('Value','median'),Mean=('Value','mean')).reset_index()
    overall['MissingRate']=overall.Missing/overall.Participants
    return result, overall

def write_database(bio,demo,long,grouped):
    file=ROOT/'data/processed/nhanes.sqlite'
    with sqlite3.connect(file) as con:
        con.execute('PRAGMA foreign_keys=ON')
        for view in ['v_grouped_stats','v_missingness','v_long','v_adults','v_joined']:
            con.execute(f'DROP VIEW IF EXISTS {view}')
        for table in ['lab_measurements','nhanes_bio','nhanes_demo']:
            con.execute(f'DROP TABLE IF EXISTS {table}')
        con.executescript((ROOT/'sql/02_schema.sql').read_text())
        for table,df in [('nhanes_demo',demo),('nhanes_bio',bio),('lab_measurements',long)]:
            records=json.loads(df.to_json(orient='records',double_precision=15))
            values=[tuple(row[col] for col in df.columns) for row in records]
            con.executemany(f'INSERT INTO {table} VALUES ({",".join("?" for _ in df.columns)})',values)
        con.executescript((ROOT/'sql/03_views.sql').read_text())
        sql_long=pd.read_sql_query('SELECT * FROM v_long ORDER BY SEQN, Biomarker',con)
        expected=long.sort_values(['SEQN','Biomarker']).reset_index(drop=True)
        compare_cols=['SEQN','Biomarker','Value','IsMissing','Unit','SexLabel','AgeBand']
        pd.testing.assert_frame_equal(sql_long[compare_cols],expected[compare_cols],check_dtype=False,rtol=1e-12)
        sql_stats=pd.read_sql_query('SELECT * FROM v_grouped_stats ORDER BY Biomarker, Unit, SexLabel, AgeBand',con)
        expected_stats=grouped.sort_values(['Biomarker','Unit','SexLabel','AgeBand']).reset_index(drop=True)
        pd.testing.assert_frame_equal(sql_stats[expected_stats.columns],expected_stats,check_dtype=False,rtol=1e-12)
        if con.execute('PRAGMA integrity_check').fetchone()[0]!='ok': raise ValueError('SQLite integrity failure')
        if con.execute('PRAGMA foreign_key_check').fetchall(): raise ValueError('SQLite foreign-key violation')
        sql_stats.to_csv(ROOT/'reports/sql_reconciliation.csv',index=False)
    return {'long_rows_compared':len(long),'group_rows_compared':len(grouped),'sqlite_integrity':'ok','foreign_key_violations':0}

def export_csv(df,name):
    path=ROOT/'data/processed'/f'{name}.csv'
    df.to_csv(path,index=False)
    restored=pd.read_csv(path,dtype={c:'Int64' for c in df.columns if str(df[c].dtype)=='Int64'})
    pd.testing.assert_frame_equal(restored,df.reset_index(drop=True),check_dtype=False,rtol=1e-12)

def main(download=False):
    for path in ['data/processed','reports/figures']: (ROOT/path).mkdir(parents=True,exist_ok=True)
    bio,demo=get_sources(download)
    b,d,joined,adults,long,log,bounds=prepare(bio,demo)
    grouped,overall=summaries(long)
    for name,frame in [('bio_source',b),('demo_source',d),('joined',joined),('adults_wide',adults),
                       ('measurements_long',long),('missingness_by_group',grouped),('biomarker_summary',overall),
                       ('cleaning_log',log),('iqr_review_bounds',bounds)]: export_csv(frame,name)
    audit=write_database(b,d,long,grouped)
    audit.update({'source_biochemistry_rows':len(b),'source_demographics_rows':len(d),'joined_rows':len(joined),
                  'adult_rows':len(adults),'excluded_under_20':len(joined)-len(adults),'long_rows':len(long),
                  'missing_measurements':int(long.IsMissing.sum()),'observed_measurements':int(long.Value.notna().sum()),
                  'imputed_values':0,'outliers_removed':0,'raw_hashes_verified':True,
                  'analysis_scope':'Unweighted adult sample descriptions; not population estimates'})
    if len(long)!=len(adults)*6 or long.duplicated(['SEQN','Biomarker']).any(): raise ValueError('Long-form key/row invariant failure')
    (ROOT/'reports/validation.json').write_text(json.dumps(audit,indent=2)+'\n')
    # A compact typed intermediate feeds the artifact-tool workbook builder.
    def matrix(frame): return [list(frame.columns)]+frame.astype(object).where(frame.notna(),None).values.tolist()
    payload={name:matrix(frame) for name,frame in [('bio',b),('demo',d),('adults',adults),('long',long),('summary',overall),('grouped',grouped),('log',log),('bounds',bounds)]}
    payload['validation']=audit
    (ROOT/'reports/workbook_data.json').write_text(json.dumps(payload,allow_nan=False))
    from reporting import make_report
    make_report(ROOT,overall,grouped,audit,bounds)
    print(json.dumps(audit,indent=2))
    return audit

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--download',action='store_true',help='Re-download and verify pinned CDC source files')
    args=parser.parse_args()
    main(args.download)
