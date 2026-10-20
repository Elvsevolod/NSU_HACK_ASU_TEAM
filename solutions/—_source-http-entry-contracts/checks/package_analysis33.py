"""Build a source/evidence handoff; no weights, runtime, cookies or uploads."""
import argparse,hashlib,json,re,zipfile
from pathlib import Path
V=Path(__file__).resolve().parents[1];ROOT=V.parents[1]


def sha(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True)
    p.add_argument('--candidate',default='solution.zip');p.add_argument('--metadata',default='benchmark/candidate-metadata.json')
    p.add_argument('--replay',default='benchmark/candidate-replay/replay.json')
    p.add_argument('--capture',default='benchmark/candidate-replay-capture/run.json');a=p.parse_args()
    assert Path(a.candidate).name==a.candidate
    assert not Path(a.metadata).is_absolute() and '..' not in Path(a.metadata).parts
    replay=json.loads((V/a.replay).read_text())
    assert not a.output.exists();assert replay['passed'] and replay['archive_sha256']==sha(V/a.candidate)
    assert json.loads((V/a.capture).read_text())['returncode']==0
    metadata=json.loads((V/a.metadata).read_text())
    assert all(sha(V/'code'/name)==digest for name,digest in metadata['code_sha256'].items())
    assert sha(V/'submission.json')==metadata['submission_sha256']
    files={};excluded=[]
    def add(root,prefix):
        for file in sorted(root.rglob('*')):
            if file.is_dir():continue
            assert not file.is_symlink(),file
            if {'__pycache__','.pytest_cache','.git','.venv'}&set(file.parts) or file.name=='.DS_Store' or file.suffix in ('.pyc','.tmp','.lock'):
                excluded.append(str(file.relative_to(root)));continue
            assert file.name not in ('cookies.json','storage-state.json','session-state.json') and file.suffix!='.har'
            if file.suffix in ('.json','.md','.txt','.py','.sql','.properties'):
                assert not re.search(rb'participant_\d+@techarena_nsuts\.ru',file.read_bytes()),file
            files[prefix+'/'+file.relative_to(root).as_posix()]=file
    add(V,'solution_33')
    for part in ('targets','skeleton','context','scenarios','gold','platform'):add(ROOT/'tt-challenge'/part,'inputs/tt-challenge/'+part)
    for name in ('README.md','REFERENCE.md'):files['inputs/tt-challenge/'+name]=ROOT/'tt-challenge'/name
    start='''# Аналитика решения №33\n\nНачните с [причинного разбора](solution_33/CAUSAL_REVIEW.md), затем [статусов](solution_33/STATUS_MATRIX.md) и [воспроизведения](solution_33/REPRODUCE.md).\n\nВнутри — code/submission/solution.zip №33, патч к неизменённому №32, raw модельные результаты и paired execution, frozen source datasets и полный исходный TT input для offline replay. Parent32 assessed ZIP сохранён отдельно. Веса и model runtime не включены; для обычного анализатора они не нужны. Лицензии/revisions/metadata и scripts приложены.\n\nЭто зафиксированная итерация E2. Full semantic transfer остаётся failed/partial, goal R01–R08 активен. На сайт кандидат не отправлен. Ranking holdout и execution/state проверки имеют разные знаменатели. Gold, labels и oracle предназначены только checker; inference их не читает.\n\nMANIFEST.json задаёт SHA256 каждого файла. Финальный receipt проверки этого ZIP находится рядом с архивом, а не внутри него. Проверить заново можно checks/check_analysis33.py из solution_33. Исторические и сторонние Markdown сохранены как данные; их внутренние относительные ссылки не объявлены полностью переносимыми. Основные документы решения проверены на существование ссылок.\n'''.encode()
    stage=metadata['source_stage']
    start=start.decode().replace('Это зафиксированная итерация E2.', 'Это зафиксированный этап '+stage+'.')
    start=start.replace('code/submission/solution.zip №33', 'code/submission/'+a.candidate+' №33')
    start+=('\nТекущий кандидат: '+a.candidate+'; metadata: '+a.metadata+'.\n'
        'Аргументы повторной проверки: --candidate '+a.candidate+' --metadata '+a.metadata+'.\n'
        'Сохранённый solution.zip относится к историческому E2.\n')
    start=start.encode()
    manifest={name:sha(file) for name,file in sorted(files.items())};manifest['START_HERE.md']=hashlib.sha256(start).hexdigest()
    a.output.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(a.output,'x',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for name,file in sorted(files.items()):z.write(file,name)
        z.writestr('START_HERE.md',start);z.writestr('MANIFEST.json',json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    receipt={'archive_sha256':sha(a.output),'bytes':a.output.stat().st_size,'members':len(manifest)+1,
        'candidate':a.candidate,'metadata':a.metadata,'stage':stage,
        'candidate_sha256':sha(V/a.candidate),'submission_sha256':sha(V/'submission.json'),
        'omissions':'Generated cache/OS/lock metadata only; model weights/runtime outside variant were never selected',
        'excluded':excluded,'verification':'pending separate extraction/replay'}
    a.output.with_suffix('.build.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:v for k,v in receipt.items() if k!='excluded'}))


if __name__=='__main__':main()
