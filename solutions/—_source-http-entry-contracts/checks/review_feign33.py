"""Causal E3/E4 evidence, without changing the independent partial oracle."""
import difflib
import hashlib
import json
from pathlib import Path
from transfer_semantics import inspect_semantics
from check_source_state import evaluate

V=Path(__file__).resolve().parents[1]


def read(path):return json.loads(path.read_text())


def main():
    output=V/'development/feign-review';output.mkdir(exist_ok=False)
    old=V/'development/stages/E3-json-property/code'
    new=V/'development/stages/E4-feign-contracts/code'
    patch=[];changed=[]
    for name in sorted({p.relative_to(root) for root in (old,new) for p in root.rglob('*') if p.is_file()}):
        a=(old/name).read_text() if (old/name).is_file() else ''
        b=(new/name).read_text() if (new/name).is_file() else ''
        if a==b:continue
        changed.append(str(name));patch.extend(difflib.unified_diff(a.splitlines(True),b.splitlines(True),fromfile='E3/'+str(name),tofile='E4/'+str(name)))
    (output/'code.patch').write_text(''.join(patch))
    projects={};witnesses={}
    for project in ('organization','library'):
        projects[project]={}
        for stage,folder in (('e3',V/'benchmark/json-property-paired'/(project+'-e3')),
                             ('e4',V/'benchmark/feign-boundary-paired-02'/project)):
            semantic=inspect_semantics(project,folder,V/'development/transfer')
            (output/(project+'-'+stage+'-semantics.json')).write_text(json.dumps(semantic,indent=2)+'\n')
            measures={}
            for mode in ('explicit','nl'):
                report=read(folder/mode/'report.json');states=evaluate(project,report)
                (output/(project+'-'+stage+'-'+mode+'-states.json')).write_text(json.dumps(states,indent=2)+'\n')
                checks=[c for c in semantic['checks'] if c['mode']==mode]
                measures[mode]={'denominator':len(checks),'partial_steps_passed':sum(c['passed'] for c in checks),
                    **{key:sum(c['checks'][key] for c in checks) for key in ('handler','wire','completion','required_edges','exploration_complete')},
                    'states_passed':sum(c['passed'] for c in states['checks']),'state_denominator':len(states['checks']),
                    'environment':report['environment'],'input_sha256':report['input_sha256']}
                if project=='library' and mode=='explicit':
                    alternatives=report['scenarios']['library-create-and-select']['steps'][0]['alternatives']
                    witnesses[stage]=[{'parameters':a['parameters'],'requests':a['requests'],'outcome':a['outcome'],
                        'unresolved':a['unresolved'],'data_operations':a['data_operations'],'state_after':a['state_after']} for a in alternatives]
            projects[project][stage]=measures
        for mode in ('explicit','nl'):
            assert projects[project]['e3'][mode]['environment']==projects[project]['e4'][mode]['environment']
            assert projects[project]['e3'][mode]['input_sha256']==projects[project]['e4'][mode]['input_sha256']
    tt={}
    for stage in ('E2-source-contracts','E3-json-property','E4-feign-contracts'):
        folder=V/'benchmark/stages'/stage
        tt[stage]={'summary':read(folder/'summary.json'),'evaluation':read(folder/'evaluation.json')}
    result={'stage':'E4-feign-contracts','changed_code_files':changed,'projects':projects,'library_first_step':witnesses,
        'tt':tt,'full_transfer_verified':False,'model_adoption':'experiment_rejected; unchanged',
        'interpretation':'Literal Feign path and native annotation identity repaired. Observed unmodeled source interceptor now stops dispatch; no fabricated outbound headers or target execution.',
        'regression_fixed':'First broad interceptor guard broke supported Piggy OAuth2. Exact one-return native factory plus supplied verified context restores the accepted contract; no blanket exemption.',
        'instrumentation_correction':'Initial Feign fixture assertions counted Engine.run outer request and treated public request dictionaries as Request objects. Corrected expectations rerun on frozen E3: 9 fail / 2 pass.',
        'evidence':{'corrected_before':'benchmark/feign-path-before-corrected','targeted_after':'benchmark/feign-boundary-tests-03',
            'full':'benchmark/feign-boundary-full-02','checker':'benchmark/feign-boundary-checker',
            'rejected_integration':'benchmark/feign-boundary-integration/results.json',
            'accepted_integration':'benchmark/feign-boundary-integration-02/results.json','source':'development/feign-preflight/sources.json'},
        'next':'Source RequestInterceptor registration/order/RequestTemplate effects, independently frozen controls before implementation; fresh complete real holdouts remain pending.',
        'patch_sha256':hashlib.sha256((output/'code.patch').read_bytes()).hexdigest(),'targets_started':False}
    (output/'review.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'changed_code_files':changed,'full_transfer_verified':False,'tt_answers_unchanged':len({r['summary']['submission_sha256'] for r in tt.values()})==1}))


if __name__=='__main__':main()
