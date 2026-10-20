"""Record the JsonProperty-only intervention against frozen E2 source inputs."""
import difflib
import hashlib
import json
from pathlib import Path
from check_source_state import evaluate
from transfer_semantics import inspect_semantics

V=Path(__file__).resolve().parents[1]


def read(path):return json.loads(path.read_text())


def main():
    output=V/'development/json-property-review';output.mkdir(exist_ok=False)
    before=V/'development/stages/E2-source-contracts/code'
    after=V/'development/stages/E3-json-property/code'
    delta=[];changed=[]
    files={p.relative_to(root) for root in (before,after) for p in root.rglob('*') if p.is_file()}
    for name in sorted(files):
        old=(before/name).read_text() if (before/name).is_file() else ''
        new=(after/name).read_text() if (after/name).is_file() else ''
        if old==new:continue
        changed.append(str(name));delta.extend(difflib.unified_diff(old.splitlines(True),new.splitlines(True),
            fromfile='E2/'+str(name),tofile='E3/'+str(name)))
    (output/'code.patch').write_text(''.join(delta))
    projects={}
    for name in ('organization','library'):
        projects[name]={}
        for stage in ('e2','e3'):
            folder=V/'benchmark/json-property-paired'/(name+'-'+stage)
            semantics=inspect_semantics(name,folder,V/'development/transfer')
            (output/(name+'-'+stage+'-semantics.json')).write_text(json.dumps(semantics,indent=2)+'\n')
            measures={}
            for mode in ('explicit','nl'):
                report=read(folder/mode/'report.json')
                state=evaluate(name,report)
                (output/(name+'-'+stage+'-'+mode+'-state.json')).write_text(json.dumps(state,indent=2)+'\n')
                checks=[c for c in semantics['checks'] if c['mode']==mode]
                measures[mode]={'denominator':len(checks),'partial_steps_passed':sum(c['passed'] for c in checks),
                    **{key:sum(c['checks'][key] for c in checks) for key in
                       ('handler','wire','completion','required_edges','exploration_complete')},
                    'states_passed':sum(c['passed'] for c in state['checks']),'states_denominator':len(state['checks']),
                    'environment':report['environment'],'input_sha256':report['input_sha256']}
            projects[name][stage]=measures
    witnesses={}
    for stage in ('e2','e3'):
        folder=V/'benchmark/json-property-paired'/('library-'+stage)
        report=read(folder/'explicit/report.json')
        step=report['scenarios']['library-create-and-select']['steps'][0]
        witnesses[stage]=[{'bound_arguments':a['requests'][0]['bound_arguments'],
            'unresolved':a['unresolved'],'outcome':a['outcome'],
            'first_remote_boundary':[v for v in a['unresolved'] if 'Feign' in v]} for a in step['alternatives']]
    for project in projects.values():
        for mode in ('explicit','nl'):
            assert project['e2'][mode]['input_sha256']==project['e3'][mode]['input_sha256']
            assert project['e2'][mode]['environment']==project['e3'][mode]['environment']
    result={'stage':'E3-json-property','changed_code_files':changed,'projects':projects,
        'library_binding_witness':witnesses,'full_transfer_verified':False,
        'interpretation':'DTO binding repaired; unchanged partial chain gates expose a later Feign path boundary. No full precision/IoU claim.',
        'regression_tests':{'before':'benchmark/json-property-before','targeted_after':'benchmark/json-property-after',
            'full_after':'benchmark/json-property-full','integration':'benchmark/json-property-integration'},
        'tt_stage':'benchmark/stages/E3-json-property','source_reading':'development/json-property-preflight/sources.json',
        'source_preparation_oracle_used_predictions':False,'targets_started':False,
        'patch_sha256':hashlib.sha256((output/'code.patch').read_bytes()).hexdigest()}
    (output/'review.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'changed_code_files':changed,'full_transfer_verified':False}))


if __name__=='__main__':main()
