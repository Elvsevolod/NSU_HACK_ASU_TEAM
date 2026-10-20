"""Compact version31 evidence, exact extraction hashes and runnable-content checks."""
import argparse,hashlib,json,os,posixpath,re,shutil,subprocess,sys,tempfile,time,zipfile
from pathlib import Path
from archive_support import verified_manifest,execute
V=Path(__file__).resolve().parents[1]
PREFIX='solution_31/'


def sha(path):
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def read(path):return json.loads(path.read_text())


def exclusion(path):
    rel=path.relative_to(V).as_posix();parts=Path(rel).parts
    if {'__pycache__','.pytest_cache','.git','.venv'}&set(parts) or path.name=='.DS_Store' or path.suffix in ('.pyc','.class','.jar','.lock','.tmp'):return 'generated cache/OS/lock metadata'
    if rel=='PACKAGE_OMISSIONS.json':return 'regenerated package omission index'
    if rel.startswith('benchmark/stages/') and path.name=='analysis-report.json.gz' and parts[2]!='G01-parent30':return 'redundant intermediate full report: code snapshot, exact hash, summary and full103 comparisons retained; regenerate with --existing-snapshot --output and complete TT input'
    if rel.startswith('development/historical30/') and path.name=='analysis-report.json.gz':return 'historical full report outside S6: complete S6 projection and original full-report SHA retained; not all old scenario traces duplicated'
    if rel=='benchmark/archive-replay/analysis-report.json':return 'repeat full diagnostic report duplicates final measured code analysis scope; exact replay receipt/audit/tests/submission retained; rerun exact ZIP for a new report'
    if rel in ('benchmark/server-archive.zip','benchmark/restored-best-server.zip'):return 'downloaded archive duplicate: candidate equals included solution.zip; old best5 is represented only by exact SHA/receipt'
    if rel.startswith('benchmark/replay-negative/') and path.suffix=='.zip':return 'generated deliberately invalid wrapper fixture; generator and actual failure/timeout receipts retained'
    return None


def document_links(manifest,contents):
    missing=[]
    for name,payload in contents.items():
        for target in re.findall(r'\]\(([^)]+)\)',payload.decode()):
            if target.startswith(('http:','https:','#')):continue
            resolved=posixpath.normpath(posixpath.join(str(Path(name).parent),target.split('#')[0]))
            if resolved not in manifest and not any(n.startswith(resolved.rstrip('/')+'/') for n in manifest):missing.append([name,resolved])
    return missing


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--verified-from',type=Path);a=p.parse_args()
    a.output=a.output.resolve();assert not a.output.exists();a.output.parent.mkdir(parents=True,exist_ok=True)
    for n in ('benchmark/final/witness-check.json','benchmark/archive-replay/replay.json','benchmark/protected-integrity-final.json'):
        assert read(V/n)['passed'],n
    site=read(V/'benchmark/site-score.json') if (V/'benchmark/site-score.json').exists() else {'status':'pending'}
    if site['status']=='verified':
        assert read(V/'benchmark/server-verification.json')['passed']
        assert read(V/'benchmark/site-best-restored.json')['passed']
    selected=[];omitted=[]
    for path in sorted(V.rglob('*')):
        if path.is_dir():continue
        assert not path.is_symlink(),path
        reason=exclusion(path)
        if reason:
            if reason not in ('generated cache/OS/lock metadata','regenerated package omission index'):
                omitted.append({'path':path.relative_to(V).as_posix(),'sha256':sha(path),'bytes':path.stat().st_size,'reason':reason})
            continue
        assert path.name not in ('cookies.json','storage-state.json','session-state.json') and path.suffix!='.har',path
        if path.suffix in ('.json','.md','.txt','.py','.sql','.properties'):
            assert not re.search(rb'participant_\d+@techarena_nsuts\.ru',path.read_bytes()),'judge credentials in '+str(path)
        selected.append(path)
    omission={'schema':'package-omissions/31','omitted_outputs':omitted,
      'external_inputs':[{'path':'tt-challenge/targets/trainticket','hashes':'development/protected-files.json entries with this prefix','impact':'full TT offline replay requires the original source tree'},
        {'path':'tt-challenge/skeleton,context,scenarios','hashes':'development/input-sha256.json','impact':'needed for full TT replay; not replaced by gold/submission'}],
      'preserved':['current source/checkers/tests and complete regression profiles','full final and parent30 baseline reports','complete historical S6 projections','all stage code/manifests/deltas/commands and own failed experiments','exact assessed solution.zip plus score/restore receipts'],
      'not_claimed':'No omitted intermediate/historical full report is claimed present. Runtime/timing bytes are not recreated exactly by a new run.'}
    omission_bytes=(json.dumps(omission,ensure_ascii=False,indent=2)+'\n').encode();(V/'PACKAGE_OMISSIONS.json').write_bytes(omission_bytes)
    intro='''# Аналитический архив решения №31

Начните с [результатов и таблицы G01–G18](solution_31/FINAL_REVIEW.md), затем [воспроизведения](solution_31/REPRODUCE.md) и [ограничений](solution_31/LIMITATIONS.md).

Внутри только новый вариант и необходимые доказательства: typed collection/Map filter/Stream/Optional/MVC/PATCH/reduce, полная корзина, причинный S6 ledger и оставшийся TT frontier. G06 integration rejected, G15 not_run; универсальность и полная TT NL-цепочка не заявлены. Сайт и восстановление №5 — отдельные реальные receipts; score не заменяет source-semantic проверки.

Точный judge ZIP — solution_31/solution.zip. README внутри него — pre-site snapshot; внешний README/FINAL_REVIEW обновлены после оценки. Код/ответ/оценённый ZIP не пересобраны.

MANIFEST.json покрывает каждый файл кроме самой hash-карты. PACKAGE_OMISSIONS.json внутри solution_31 перечисляет точные hashes исключённых избыточных full reports и внешних TT inputs; baseline/final reports, все103 step deltas и stage snapshots сохранены. Полная история репозитория и старый best5 ZIP не включены. Реальные credentials/cookies/session dumps не включены; статические test credentials в source fixtures — часть входов проверки.
'''.encode()
    extras={'START_HERE.md':intro,PREFIX+'PACKAGE_OMISSIONS.json':omission_bytes}
    manifest={PREFIX+f.relative_to(V).as_posix():sha(f) for f in selected}
    manifest.update({n:hashlib.sha256(b).hexdigest() for n,b in extras.items()})
    docs={'START_HERE.md':intro,**{PREFIX+n:(V/n).read_bytes() for n in ('README.md','FINAL_REVIEW.md','IMPLEMENTATION_REVIEW.md','LIMITATIONS.md','REPRODUCE.md')}}
    missing=document_links(manifest,docs)
    assert not missing,missing
    runnable={n:d for n,d in manifest.items() if any(n.startswith(PREFIX+s) for s in ('code/','checks/','validation_inputs/','development/oracles/','development/cart-historical30/')) or n==PREFIX+'requirements.txt'}
    runnable_sha=hashlib.sha256(json.dumps(runnable,sort_keys=True).encode()).hexdigest()
    with zipfile.ZipFile(a.output,'x',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for file in selected:z.write(file,PREFIX+file.relative_to(V).as_posix())
        for n,b in extras.items():z.writestr(n,b)
        z.writestr('MANIFEST.json',json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    result={'passed':False,'archive':str(a.output),'sha256':sha(a.output),'bytes':a.output.stat().st_size,'files':len(manifest)+1,
        'all_member_hashes_match':False,'runnable_content_sha256':runnable_sha,'site_status':site['status'],
        'omitted_outputs':len(omitted),'credentials_included':False,'old_solution_trees_included':False,'verification_runs':{}}
    result['relative_document_links_checked']=True
    verification=a.output.with_suffix('.verification');assert not verification.exists();verification.mkdir()
    try:
        with tempfile.TemporaryDirectory(prefix='analysis31-extract-') as directory:
            root=Path(directory)
            with zipfile.ZipFile(a.output) as z:verified_manifest(z,'MANIFEST.json');z.extractall(root)
            assert all(sha(root/n)==d for n,d in manifest.items())
            extracted=root/'solution_31';assert sha(extracted/'solution.zip')==read(extracted/'benchmark/archive-check.json')['sha256']
            result['all_member_hashes_match']=True;result['inner_judge_zip_matches_tested_archive']=True
            if a.verified_from:
                prior=read(a.verified_from);assert prior['passed'] and prior['runnable_content_sha256']==runnable_sha
                result['reused_exact_runnable_verification']={'source':str(a.verified_from),'source_sha256':sha(a.verified_from),'same_runnable_content':True}
                valid=True
            else:
                environment={**os.environ,'PYTHONPATH':str(extracted/'code'),'PYTHONDONTWRITEBYTECODE':'1'}
                commands={'tests':[sys.executable,'-B','-m','pytest','code/tests','checks/tests','-q','-p','no:cacheprovider'],
                    'profiles':[sys.executable,'-B','checks/run_regression_gate.py','--output',str(root/'profile-replay')]}
                for label,command in commands.items():result['verification_runs'][label]=execute(command,extracted,environment,verification,label,180)
                valid=all(r['returncode']==0 for r in result['verification_runs'].values())
            result['passed']=valid
    except Exception as error:result['failure']={'type':type(error).__name__,'message':str(error)}
    finally:
        a.output.with_suffix('.check.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='verification_runs'},ensure_ascii=False));assert result['passed']


if __name__=='__main__':main()
