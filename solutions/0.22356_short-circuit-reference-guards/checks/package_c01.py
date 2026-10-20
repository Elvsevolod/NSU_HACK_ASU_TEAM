"""Validate the actual C01 source, graph delta and immutable upload artifact."""
from collections import Counter
import difflib
import hashlib
import json
from pathlib import Path
import re
import zipfile

V=Path(__file__).resolve().parents[1]
ROOT=V.parents[1]
PARENT=ROOT/'solutions/—_source-http-entry-contracts'
CYCLE=ROOT/'competition_cycles/C01-short-circuit'


def read(path):return json.loads(path.read_text())
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def save(path,value):path.write_text(json.dumps(value,ensure_ascii=True,indent=2)+'\n')
def graph(document,sid):return {(e['source'],e['relation'],e['target']) for e in document['scenarios'][sid]['edges']}
def semantic_digest(document):
    return hashlib.sha256(json.dumps({sid:sorted(graph(document,sid)) for sid in sorted(document['scenarios'])},sort_keys=True).encode()).hexdigest()


def main():
    code={p.relative_to(V/'code').as_posix():sha(p) for p in sorted((V/'code').rglob('*')) if p.is_file() and '__pycache__' not in p.parts}
    for label in ('c01-full','tt-c01-command'):
        capture=read(V/'benchmark'/label/'run.json')
        assert capture['returncode']==0 and capture['code_sha256']==code
    assert read(V/'benchmark/c01-piggy-check-command/run.json')['returncode']==0
    evaluation=read(V/'benchmark/evaluation.json');fmt=read(V/'benchmark/format-check.json')
    assert not any((evaluation['errors'],evaluation['warnings'],fmt['errors'],fmt['warnings']))
    before=read(PARENT/'submission.json');after=read(V/'submission.json')
    answer_digest=semantic_digest(after);duplicates=[]
    for candidate in (ROOT/'solutions').glob('*/submission.json'):
        if candidate.parent==V:continue
        if semantic_digest(read(candidate))==answer_digest:duplicates.append(str(candidate))
    assert not duplicates,('duplicate answer',duplicates)
    delta={};outcomes=Counter();budget_causes=Counter()
    report=read(V/'benchmark/tt-c01/report.json')
    for sid,scenario in report['scenarios'].items():
        a,b=graph(before,sid),graph(after,sid);added,removed=b-a,a-b
        union={tuple(edge[k] for k in ('source','relation','target')) for step in scenario['steps']
               for alt in step['alternatives'] for edge in alt['edges']}
        assert union==b,'Export differs from observed alternatives'
        delta[sid]={'added':sorted(added),'removed':sorted(removed),'before':dict(Counter(e[1] for e in a)),
            'after':dict(Counter(e[1] for e in b))}
        for step in scenario['steps']:
            for alt in step['alternatives']:
                outcomes[alt['outcome']]+=1
                assert alt['exploration']['path_limit']==4 and alt['exploration']['completion_budget']==8
                if alt['outcome']=='analysis completion budget exhausted':
                    budget_causes[next((x['cause'] for x in alt['knowledge_losses'] if x['phase']=='budget'),'unrecorded')]+=1
    old_manifest=read(PARENT/'development/stages/E28-opaque-stream-lifecycle/code-sha256.json')
    changed=[name for name in sorted(set(code)|set(old_manifest)) if code.get(name)!=old_manifest.get(name)]
    assert {n for n in changed if not n.startswith('tests/')}=={'analyzer/engine.py','analyzer/constraints.py'}
    patch=[]
    for name in changed:
        a=(PARENT/'development/stages/E28-opaque-stream-lifecycle/code'/name)
        old=a.read_text() if a.exists() else '';new=(V/'code'/name).read_text()
        patch.extend(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='parent33-e28/'+name,tofile='variant34/'+name))
    (V/'development/C01.patch').write_text(''.join(patch))
    save(V/'benchmark/edge-delta.json',delta)
    summary={k:report[k] for k in ('source_fingerprint','input_sha256','preparation_seconds','analysis_seconds','elapsed_seconds','peak_rss_bytes','constraints','retrieval_profile','path_limit')}
    summary.update(outcomes=dict(outcomes),budget_causes=dict(budget_causes),added_edges=sum(len(x['added']) for x in delta.values()),
        removed_edges=sum(len(x['removed']) for x in delta.values()),submission_sha256=sha(V/'submission.json'),semantic_answer_sha256=answer_digest,
        assessment='Measured experiment, not accepted as a quality gain. Budget alternatives rose302→321; final delta onlyS5/S6. Await site comparison.')
    save(V/'benchmark/cycle-summary.json',summary)
    tests=int(re.search(r'(\d+) passed',(V/'benchmark/c01-full/stdout.txt').read_text())[1])
    metadata={'variant':34,'cycle':'C01-short-circuit','parent_variant':33,'parent_stage':'E28-opaque-stream-lifecycle',
        'parent_archive_sha256':sha(PARENT/'solution-e28.zip'),'parent_submission_sha256':sha(PARENT/'submission.json'),
        'code_sha256':code,'code_manifest_sha256':hashlib.sha256(json.dumps(code,sort_keys=True).encode()).hexdigest(),
        'submission_sha256':sha(V/'submission.json'),'semantic_answer_sha256':answer_digest,'code_tests':tests,
        's0':evaluation['score'],'site_submission_id':None,'site_score':None,'site_verdict':None,'budgets_unchanged':True,
        'target_apps_started':False,'model_required':False,'duplicates_detected':duplicates,'production_changes':changed,
        'quality_gate':'local format/replay plus site experiment; no success claim from tests or fewer warnings'}
    save(V/'benchmark/candidate-metadata.json',metadata)
    text=(V/'README.md').read_text().replace('— (не измерен)',str(evaluation['score']),1)
    sets=evaluation['scenarios']['S0']['sets'];text=text.replace('| S0: executes / calls / remote / data | — |',
        '| S0: executes / calls / remote / data | '+' / '.join(str(sets[k]['iou']) for k in ('executes','calls','remote','data'))+' |')
    text=text.replace('| Формат S0–S7 | Не проверен |','| Формат S0–S7 | Ошибок и предупреждений нет |')
    text=text.replace('| Время построения ответа | Не измерено |',f"| Время построения ответа | {report['elapsed_seconds']} с; Python3.11.9, локально |")
    text+='\nИзмеренный ответ: +6/−58 рёбер, толькоS5/S6; budget alternatives302→321. Это эксперимент с риском потери полезных продолжений, не объявленное улучшение качества. S0 и сайт — отдельные показатели. Независимые source controls before/after,2453 локальных теста и8-шаговая PiggyMetrics цепочка пройдены. Полный raw trace и причины сохранены отдельно; source/report hashes есть в metadata.\n'
    (V/'README.md').write_text(text)
    files={'code/'+name:V/'code'/name for name in code}
    for name in ('README.md','requirements.txt','submission.json','benchmark/candidate-metadata.json',
                 'benchmark/format-check.json','benchmark/evaluation.json','benchmark/edge-delta.json','benchmark/cycle-summary.json'):
        files[name]=V/name
    manifest={name:sha(path) for name,path in sorted(files.items())}
    archive=V/'solution.zip';assert not archive.exists()
    with zipfile.ZipFile(archive,'x',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for name,path in sorted(files.items()):assert not path.is_symlink();z.write(path,name)
        z.writestr('benchmark/package-manifest.json',json.dumps(manifest,indent=2)+'\n')
    receipt={'archive_sha256':sha(archive),'bytes':archive.stat().st_size,'members':len(files)+1,
        'code_manifest_sha256':metadata['code_manifest_sha256'],'submission_sha256':metadata['submission_sha256'],
        'semantic_answer_sha256':answer_digest,'local_validated':True,'actual_replay':'pending','uploaded':False,
        'edge_delta':{'added':summary['added_edges'],'removed':summary['removed_edges']},'site_submission_id':None,'site_score':None}
    save(V/'benchmark/package-receipt.json',receipt);save(CYCLE/'package-receipt.json',receipt)
    print(json.dumps(receipt))


if __name__=='__main__':main()
