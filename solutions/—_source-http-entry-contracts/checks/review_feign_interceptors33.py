"""Compare frozen E4/E6 runs against unchanged independent partial obligations."""
import difflib
import hashlib
import json
from pathlib import Path
from transfer_semantics import inspect_semantics
from check_source_state import evaluate

V=Path(__file__).resolve().parents[1]


def read(path):return json.loads(path.read_text())


def save(path,value):path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')


def main():
    output=V/'development/feign-interceptors-review';output.mkdir(exist_ok=False)
    old=V/'development/stages/E4-feign-contracts/code';new=V/'development/stages/E6-feign-registration-controls/code'
    patch=[];changed=[]
    for name in sorted({p.relative_to(root) for root in (old,new) for p in root.rglob('*') if p.is_file()}):
        a=(old/name).read_text() if (old/name).is_file() else ''
        b=(new/name).read_text() if (new/name).is_file() else ''
        if a==b:continue
        changed.append(str(name));patch.extend(difflib.unified_diff(a.splitlines(True),b.splitlines(True),fromfile='E4/'+str(name),tofile='E6/'+str(name)))
    (output/'code.patch').write_text(''.join(patch))
    projects={};witnesses={}
    for project in ('organization','library'):
        projects[project]={}
        for stage,folder in [('e4',V/'benchmark/feign-boundary-paired-02'/project),
                             ('e6',V/'benchmark/feign-contract-controls-paired'/project)]:
            semantic=inspect_semantics(project,folder,V/'development/transfer');save(output/(project+'-'+stage+'-semantics.json'),semantic)
            measures={}
            for mode in ('explicit','nl'):
                report=read(folder/mode/'report.json');states=evaluate(project,report)
                save(output/(project+'-'+stage+'-'+mode+'-states.json'),states)
                checks=[c for c in semantic['checks'] if c['mode']==mode]
                measures[mode]={'denominator':len(checks),'partial_steps_passed':sum(c['passed'] for c in checks),
                    **{key:sum(c['checks'][key] for c in checks) for key in ('handler','wire','completion','required_edges','exploration_complete')},
                    'states_passed':sum(c['passed'] for c in states['checks']),'state_denominator':len(states['checks']),
                    'environment':report['environment'],'input_sha256':report['input_sha256']}
                if project=='library' and mode=='explicit':
                    alts=report['scenarios']['library-create-and-select']['steps'][0]['alternatives']
                    witnesses[stage]=[{'entry':a['entry'],'parameters':a['parameters'],'requests':a['requests'],
                        'outcome':a['outcome'],'data_operations':a['data_operations'],'unresolved':a['unresolved'],
                        'callbacks':a['semantic_callbacks'],'losses':a['knowledge_losses'],'state_after':a['state_after']} for a in alts]
            projects[project][stage]=measures
        for mode in ('explicit','nl'):
            assert projects[project]['e4'][mode]['environment']==projects[project]['e6'][mode]['environment']
            assert projects[project]['e4'][mode]['input_sha256']==projects[project]['e6'][mode]['input_sha256']
    tt={stage:read(V/'benchmark/stages'/stage/'summary.json') for stage in ('E4-feign-contracts','E5-source-interceptors','E6-feign-registration-controls')}
    result={'stage':'E6-feign-registration-controls','changed_code_files':changed,'projects':projects,
        'library_first_step':witnesses,'tt_answers_unchanged':len({x['submission_sha256'] for x in tt.values()})==1,
        'tt':tt,'full_transfer_verified':False,'targets_started':False,
        'causal_change':'Source Header.apply now runs before the request and its native RequestTemplate header effect carries the configured lms-key into Inventory. The next loss is the composite-ID derived repository predicate.',
        'scope':'Default Spring Boot component/configuration scanning, proven native RequestInterceptor beans, literal/Value field projection, scenario-local callback state, bounded alternative order, native Feign10.10.1 header/removeHeader semantics. Unsupported construction/configuration/template operations stop before send.',
        'evidence':{'source':'development/feign-interceptors-preflight/sources.json','before':'benchmark/feign-interceptors-before-02',
            'extra_before':'benchmark/feign-interceptors-extra-before-02','last_controls_before':'benchmark/feign-registration-path-controls-before',
            'after':'benchmark/feign-registration-path-controls-after','full':'benchmark/feign-contract-controls-full',
            'checker':'benchmark/feign-contract-controls-checker','integration':'benchmark/feign-contract-controls-integration/results.json'},
        'patch_sha256':hashlib.sha256((output/'code.patch').read_bytes()).hexdigest(),
        'next':'Run independently frozen new-app scenarios through a checked external HTTP-script driver; preserve full/partial oracle boundaries. Composite ID repository query remains an independently documented library limitation.'}
    save(output/'review.json',result)
    print(json.dumps({'changed_code_files':changed,'tt_answers_unchanged':result['tt_answers_unchanged'],
        'partial_steps':{p:{s:{m:x['partial_steps_passed'] for m,x in modes.items()} for s,modes in stages.items()} for p,stages in projects.items()},
        'full_transfer_verified':False}))


if __name__=='__main__':main()
