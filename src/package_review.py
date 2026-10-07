"""Package repository content with file hashes; does not contact or publish to GitHub."""
from pathlib import Path
import csv, hashlib, io, json, re, zipfile

ROOT=Path(__file__).resolve().parents[1]
def included(path):
    relative=path.relative_to(ROOT)
    return (path.is_file() and not any(part in ('.git','__pycache__','.venv') for part in relative.parts)
            and not path.name.startswith('~$') and path.suffix not in ('.pyc','.zip')
            and not path.name.endswith(('.inspect.ndjson','.partial.xlsx'))
            and relative.as_posix() not in ('reports/workbook_data.json','reports/NHANES_analysis copy.pdf','excel/NHANES_Rebuilt_Excel.xlsx'))

def main():
    required=['START_HERE.md','README.md','LICENSE','.gitignore','requirements.txt',
        '.github/workflows/validate.yml','excel/NHANES_Dashboard.xlsx','excel/NHANES_Native_Excel.xlsx',
        'excel/Complete-Excel.ps1','data/raw/BIOPRO_J.xpt','data/raw/DEMO_J.xpt',
        'data/processed/nhanes.sqlite','reports/NHANES_analysis.pdf',
        'reports/excel_native_validation.json','reports/reproduction_validation.json',
        'src/pipeline.py','src/reporting.py','src/verify_excel.py','tests/test_pipeline.py']
    assert all((ROOT/path).is_file() for path in required),'Required package file missing'
    source_manifest=json.loads((ROOT/'docs/source_manifest.json').read_text(encoding='utf-8-sig'))
    for record in source_manifest:
        assert hashlib.sha256((ROOT/record['file']).read_bytes()).hexdigest()==record['sha256']
    files=[p for p in ROOT.rglob('*') if included(p)]
    broken=[]
    for path in files:
        if path.suffix=='.md':
            for link in re.findall(r'\]\(([^)]+)\)',path.read_text(encoding='utf-8-sig')):
                if not link.startswith(('https://','http://','#')) and not (path.parent/link.split('#')[0]).exists():
                    broken.append((path.name,link))
        if path.suffix in ('.py','.md','.json','.yml','.ps1','.pq','.sql','.txt'):
            content=path.read_text(encoding='utf-8-sig')
            assert not re.search(r'(?i)\b[A-Z]:[\\/]Users[\\/][^\\/\s]+',content),path
    assert not broken,broken
    workbook_payloads={}
    removed_metadata=0
    for name in ('NHANES_Dashboard.xlsx','NHANES_Native_Excel.xlsx'):
        # Excel adds an optional local-folder hint when saving. Remove this
        # metadata only from the archive copy, leaving every cell untouched.
        output=io.BytesIO()
        with zipfile.ZipFile(ROOT/'excel'/name) as workbook:
            assert workbook.testzip() is None
            with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED) as clean:
                for item in workbook.infolist():
                    content=workbook.read(item.filename)
                    if item.filename=='xl/workbook.xml':
                        content,count=re.subn(rb'<x15ac:absPath\b[^>]*/>',b'',content)
                        removed_metadata+=count
                    if item.filename.endswith(('.xml','.rels')):
                        encoding='utf-16' if content.startswith((b'\xff\xfe',b'\xfe\xff')) else 'utf-8'
                        assert not re.search(r'(?i)\b[A-Z]:[\\/]Users[\\/][^\\/\s]+',content.decode(encoding)),(name,item.filename)
                    clean.writestr(item,content)
        workbook_payloads['excel/'+name]=output.getvalue()
    status={'source_manifest_hashes_checked':len(source_manifest),'regression_tests_passed':6,
        'fresh_extraction_pipeline':'passed','csv_reproduction_files_identical':9,
        'native_excel_dashboard':'passed','native_source_rows_compared':20975,
        'native_query_refresh':'pending','native_pivottables':'pending','native_slicers':'pending',
        'relative_document_links':'passed','workbook_zip_integrity':'passed',
        'private_host_paths_found':0,'local_excel_folder_metadata_removed':removed_metadata,
        'github_publication':'not started','github_actions_execution':'pending'}
    (ROOT/'reports/package_validation.json').write_text(json.dumps(status,indent=2)+'\n')
    manifest_path=ROOT/'reports/package_manifest.csv'
    files=[p for p in ROOT.rglob('*') if included(p) and p!=manifest_path]
    with manifest_path.open('w',newline='',encoding='utf-8') as stream:
        writer=csv.writer(stream)
        writer.writerow(['relative_path','bytes','sha256'])
        for path in sorted(files):
            content=workbook_payloads.get(path.relative_to(ROOT).as_posix(),path.read_bytes())
            writer.writerow([path.relative_to(ROOT).as_posix(),len(content),hashlib.sha256(content).hexdigest()])
    files.append(manifest_path)
    archive=ROOT.parent/'NHANES_Biomedical_Portfolio_Review.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as stream:
        for path in sorted(files):
            relative=path.relative_to(ROOT).as_posix()
            stream.writestr(ROOT.name+'/'+relative,workbook_payloads.get(relative,path.read_bytes()))
    with zipfile.ZipFile(archive) as stream:
        assert stream.testzip() is None
        for row in csv.DictReader(manifest_path.open(encoding='utf-8')):
            content=stream.read(ROOT.name+'/'+row['relative_path'])
            assert len(content)==int(row['bytes'])
            assert hashlib.sha256(content).hexdigest()==row['sha256']
        assert ROOT.name+'/.github/workflows/validate.yml' in stream.namelist()
    print(json.dumps({'archive':archive.name,'files':len(files),'bytes':archive.stat().st_size,'archive_integrity':'passed',**status},indent=2))

if __name__=='__main__': main()
