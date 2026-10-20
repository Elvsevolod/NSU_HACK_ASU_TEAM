"""Causal E6/E7 comparison; recheck saved traces with corrected checker only."""
import difflib
import hashlib
import json
from pathlib import Path
from semantic_holdout_checker33 import evaluate_case

V=Path(__file__).resolve().parents[1]


def read(path):return json.loads(path.read_text())


def save(path,value):path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')


def main():
    output=V/'development/integral-http-review';output.mkdir(exist_ok=False)
    old=V/'development/stages/E6-feign-registration-controls/code';new=V/'development/stages/E7-integral-http-identity/code'
    patch=[];changed=[]
    for name in sorted({p.relative_to(root) for root in (old,new) for p in root.rglob('*') if p.is_file()}):
        a=(old/name).read_text() if (old/name).is_file() else ''
        b=(new/name).read_text() if (new/name).is_file() else ''
        if a!=b:
            changed.append(str(name));patch.extend(difflib.unified_diff(a.splitlines(True),b.splitlines(True),fromfile='E6/'+str(name),tofile='E7/'+str(name)))
    (output/'code.patch').write_text(''.join(patch))
    projects={};witness={}
    for project in ('employment','healthcare'):
        package=V/'development/semantic-holdout-packages-v1'/project
        manifest=read(package/'package.json');oracle=read(package/'oracle.json')
        assert all(hashlib.sha256((package/name).read_bytes()).hexdigest()==sha for name,sha in manifest['files'].items())
        projects[project]={}
        for profile,folder in [('e6-baseline','semantic-holdout-baseline-v1'),('e6-lexical','semantic-holdout-lexical-v1'),('e7-baseline','semantic-holdout-e7-v1')]:
            checks={};run_root=V/'benchmark'/folder/project
            for run in read(run_root/'runs.json'):
                assert run['returncode']==0
                report=read(run_root/run['environment']/run['mode']/'report.json')
                audit=read(run_root/run['environment']/run['mode']/'report-offline-audit.json')
                assert not any(audit[key] for key in ('blocked_network','blocked_processes','blocked_reference_reads'))
                for sid,case in oracle['cases'].items():
                    if case['environment']==run['environment'] and case['mode']==run['mode']:
                        checks[sid]=evaluate_case(case,report['scenarios'][sid],oracle['initial_tables'])
                        if run['mode']=='explicit-script' and 'state-chain' in sid:
                            witness.setdefault(project,{})[profile]=[
                                {'step':step['n'],'requests':[a['requests'] for a in step['alternatives']],
                                 'outcomes':[a['outcome'] for a in step['alternatives']],
                                 'unresolved':[a['unresolved'] for a in step['alternatives']]}
                                for step in report['scenarios'][sid]['steps'][:4]]
            save(output/(project+'-'+profile+'-checks.json'),checks)
            counts={}
            for mode in ('explicit-script','nl-en','nl-ru'):
                selected=[row for sid,case in oracle['cases'].items() if case['mode']==mode for row in checks[sid]['steps']]
                counts[mode]={'steps':len(selected),'passed':sum(s['passed'] for s in selected),
                    'graph_exact':sum(s['checks']['graph_exact'] for s in selected),
                    'state_exact':sum(s['checks']['state_exact'] for s in selected),
                    'refusal_steps':sum('refused' in s['checks'] for s in selected)}
            projects[project][profile]=counts
        before=read(V/'benchmark/semantic-holdout-baseline-v1'/(project+'-command')/'run.json')['code_sha256']
        lexical=read(V/'benchmark/semantic-holdout-lexical-v1'/(project+'-command')/'run.json')['code_sha256']
        assert before==lexical,'A/B must use the same semantic implementation'
    summary=read(V/'benchmark/stages/E7-integral-http-identity/summary.json')
    result={'stage':'E7-integral-http-identity','changed_code_files':changed,'tt_summary':summary,
        'tt_answer_unchanged':summary['submission_sha256']=='95927fa5eb50b7d9f26d13a1c9e224bb2b803a9a6b07aa1c42996beaa15c371d',
        'projects':projects,'typed_identity_witnesses':witness,
        'source_contract':['https://docs.spring.io/spring-framework/reference/6.2/web/webmvc/mvc-controller/ann-requestmapping.html',
                           'https://docs.spring.io/spring-framework/reference/6.2/web/webmvc/mvc-controller/ann-methods/typeconversion.html'],
        'framework_docs_checked_via':'Context7; no target JVM/runtime used',
        'scope':'Canonical decimal text of proven non-null native byte/short/int/long values, same-width default Spring named-value parse; original symbolic identity retained. Narrowing and custom binders stay unresolved.',
        'checker_corrections':['Outer request1 excluded from outbound count',
            'Expected write operation/table/method and certainty checked separately for every alternative',
            'Remote counts checked per alternative'],
        'oracle_changed':False,'saved_predictions_changed':False,
        'full_semantic_transfer_verified':False,'model_adoption':'experiment_rejected; unchanged',
        'next':'Explicit Feign URL/placeholders and RequestParam; source HTTP error advice/message completeness; typed wire/order/producer checker strengthening. These observed applications are development for future tuning.',
        'patch_sha256':hashlib.sha256((output/'code.patch').read_bytes()).hexdigest()}
    save(output/'review.json',result)
    print(json.dumps({'projects':projects,'tt_answer_unchanged':result['tt_answer_unchanged'],'full_semantic_transfer_verified':False}))


if __name__=='__main__':main()
