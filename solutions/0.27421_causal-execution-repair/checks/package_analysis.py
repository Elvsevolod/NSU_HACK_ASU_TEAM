"""Bundle only this solution, its repair experiments and reviewed source profile."""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile

V=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser()
    for key in ('oracle-dir','source-repo','output'):parser.add_argument('--'+key,type=Path,required=True)
    args=parser.parse_args();assert not args.output.exists();args.output.parent.mkdir(parents=True,exist_ok=True)
    files={}
    excluded={'__pycache__','.pytest_cache','.git','.venv','preflight-doc-correction'}
    for root in ('code','checks','benchmark','development','fixtures'):
        for path in (V/root).rglob('*'):
            if path.is_file() and not excluded&set(path.parts) and path.name!='.DS_Store' and path.suffix not in ('.pyc','.class','.jar'):
                if path.name=='analysis-report.json' and path.with_suffix('.json.gz').exists():continue
                files['solution_28/'+path.relative_to(V).as_posix()]=path
    for name in ('README.md','IMPLEMENTATION_REVIEW.md','requirements.txt','submission.json','solution.zip'):
        files['solution_28/'+name]=V/name
    for path in args.oracle_dir.iterdir():
        if path.is_file() and path.name!='.DS_Store':files['source_profile/'+path.name]=path
    for path in (args.oracle_dir/'input').rglob('*'):
        if path.is_file() and path.name!='.DS_Store' and not excluded&set(path.parts):files['source_profile/input/'+path.relative_to(args.oracle_dir/'input').as_posix()]=path
    oracle=json.loads((args.oracle_dir/'additional-source-cases.oracle-reviewed-v2.json').read_text())
    for name,digest in oracle['source_sha256'].items():
        path=args.source_repo/name
        assert hashlib.sha256(path.read_bytes()).hexdigest()==digest,name
        files['source_profile/source_evidence/'+name]=path
    for path in args.source_repo.glob('LICENSE*'):
        if path.is_file():files['source_profile/source_evidence/'+path.name]=path
    manifest={name:hashlib.sha256(path.read_bytes()).hexdigest() for name,path in sorted(files.items())}
    readme='''# Решение № 28 после solution_27_regression_review.md

Начните с solution_28/IMPLEMENTATION_REVIEW.md и README.md. Внутри самостоятельный solution.zip, код, фактическая посылка и метрики сайта, полные сжатые трассы, 21 экспериментальный снимок, отрицательные проверки и source/oracle PiggyMetrics. Старые аналитические архивы и полные прежние варианты не включены; base snapshot нужен для собственных абляций ремонта.

S0 и score сайта — разные метрики. Многочисленные TT budget stops сохранены; успешный ограниченный source-профиль не доказывает универсальность. Oracle v1/v2, исправления независимого читателя и их хронология сохранены. DeepSeek не использовался. Не запускайте target приложения: команды воспроизводят только Python-анализатор.

MANIFEST.json содержит SHA-256 всех вложенных файлов. solution_28/solution.zip — неизменённый архив, отправленный на сайт; последующие сведения сайта лежат рядом, не подменяют его содержимое.
'''
    with zipfile.ZipFile(args.output,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as output:
        output.writestr('README_ANALYTICS.md',readme)
        output.writestr('MANIFEST.json',json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
        for name,path in sorted(files.items()):output.write(path,name)
    with zipfile.ZipFile(args.output) as archive:
        assert archive.testzip() is None
        assert all(hashlib.sha256(archive.read(name)).hexdigest()==digest for name,digest in manifest.items())
        assert archive.read('solution_28/solution.zip')==(V/'solution.zip').read_bytes()
    result={'sha256':hashlib.sha256(args.output.read_bytes()).hexdigest(),'bytes':args.output.stat().st_size,
        'files':len(files)+2,'all_member_hashes_match':True,'testzip':'passed','contains_only_current_solution_and_its_experiments':True,
        'archive':str(args.output.resolve()),'submission_sha256':hashlib.sha256((V/'submission.json').read_bytes()).hexdigest()}
    args.output.with_suffix('.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result,ensure_ascii=False))


if __name__=='__main__':main()
