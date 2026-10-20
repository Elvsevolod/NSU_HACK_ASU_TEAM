"""Freeze stage diffs and measured transport evidence without changing traces."""
import difflib
import argparse
import hashlib
import json
from pathlib import Path

V=Path(__file__).resolve().parents[1]
STAGES=['E7-integral-http-identity','E8-feign-wire','E9-feign-bean-decoder','E10-lombok-builder',
        'E11-http-error-values','E12-transport-values-and-witnesses','E13-stable-message-origin','E14-builder-constructor-selection']


def read(path):return json.loads(path.read_text())
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def save(path,value):path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    output=args.output.resolve();output.mkdir(exist_ok=False)
    stages={};diffs=[]
    for stage in STAGES:
        snapshot=V/'development/stages'/stage;manifest=read(snapshot/'code-sha256.json')
        assert all(sha(snapshot/'code'/name)==digest for name,digest in manifest.items())
        run=read(V/'benchmark/stages'/stage/'run.json');assert run['returncode']==0
        stages[stage]=read(V/'benchmark/stages'/stage/'summary.json')
    for old,new in zip(STAGES,STAGES[1:]):
        a=V/'development/stages'/old/'code';b=V/'development/stages'/new/'code';patch=[];changed=[]
        for name in sorted({p.relative_to(root) for root in (a,b) for p in root.rglob('*') if p.is_file()}):
            before=(a/name).read_text() if (a/name).is_file() else ''
            after=(b/name).read_text() if (b/name).is_file() else ''
            if before==after:continue
            changed.append(str(name));patch.extend(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile=old+'/'+str(name),tofile=new+'/'+str(name)))
        path=output/(old.split('-')[0]+'-to-'+new.split('-')[0]+'.patch');path.write_text(''.join(patch))
        diffs.append({'from':old,'to':new,'changed_files':changed,'patch':path.name,'sha256':sha(path)})
    gates={}
    for name in ('feign-wire-full','feign-decoder-full','lombok-builder-full','http-error-values-full','transport-values-full',
                 'message-origin-full','message-origin-checker-02','message-origin-integration-03-command',
                 'builder-selection-full','builder-selection-integration-command'):
        value=read(V/'benchmark'/name/'run.json')
        gates[name]={key:value[key] for key in ('command','cwd','python','returncode','seconds','timed_out')}
        gates[name]['stdout_sha256']=sha(V/'benchmark'/name/'stdout.txt')
    semantic=read(V/'development/transport-checker-e14/checks.json')
    counts=read(V/'development/transport-checker-e14/counts.json')
    lexical=read(V/'development/transport-checker-e14-lexical/counts.json')
    integration=read(V/'benchmark/builder-selection-integration/results.json');assert integration['passed'] and len(integration['runs'])==17
    predictions={stage:read(V/'benchmark/stages'/stage/'submission.json') for stage in STAGES}
    deltas={}
    for stage in STAGES[1:]:
        differences={}
        for sid,scenario in predictions[STAGES[0]]['scenarios'].items():
            before={(e['source'],e['relation'],e['target']) for e in scenario['edges']}
            after={(e['source'],e['relation'],e['target']) for e in predictions[stage]['scenarios'][sid]['edges']}
            if before!=after:differences[sid]={'added':[list(e) for e in sorted(after-before)],'removed':[list(e) for e in sorted(before-after)]}
        deltas[stage]=differences
    value={'current_stage':STAGES[-1],'stages':stages,'diffs':diffs,'gates':gates,'integration_passed':True,
        'baseline_retrieval_semantics':counts,'lexical_retrieval_semantics':lexical,
        'tt_answer_unchanged':stages[STAGES[-1]]['submission_sha256']==stages[STAGES[0]]['submission_sha256'],
        'intermediate_prediction_deltas_from_e7':deltas,
        'source_oracle_changed':False,'original_semantic_freeze_sha256':sha(V/'development/semantic-holdouts-frozen-v1/freeze.json'),
        'transport_oracle_extension':{'path':'development/transport-oracle-frozen-v2/freeze.json',
            'sha256':sha(V/'development/transport-oracle-frozen-v2/freeze.json'),'prepared_after_semantic_observation':True,
            'predictions_used_for_expected_values':False,'scope':'Input recipes, source declarations, original expected results/rows and ordered source repository calls'},
        'witness_checks':['Every alternative exact E/C/R/D','exact outer wire','ordered remote wire and actual encoded replies',
            'native Long binding on both sides','ordered typed SQL arguments and request origin',
            'complete agreeing history producer with observation digest','Feign message linked to the actual request/response'],
        'full_semantic_transfer_verified':False,'targets_started':False,'model_default':'experiment_rejected; unchanged',
        'next':['Prove default missing-route dispatch before treating an absent handler as HTTP404',
                'Analyze paired NL candidate/refusal and value-origin failures without retuning on observed apps',
                'Evaluate the preregistered new retrieval extension using fixed old CodeRank and thresholds'],
        'failure_interpretation':{'e11_full':'Two legacy fixtures lacked native HttpStatus imports; imports added and strict assertions retained. Source namesake controls require source dispatch.',
            'e10_to_e13_tt_s4':'The new builder guard rejected a source no-arg constructor despite a proven native generated AllArgsConstructor. Three later S4 edges disappeared; E14 checks exact generated constructor selection without invoking the unrelated no-arg body.',
            'e12_message_origin':'The new full origin check exposed a digest/serialized-datetime discrepancy. E13 uses the report scalar representation; no response bytes invented.',
            'initial_integration':'New native_kind metadata was rejected by historical exact dictionaries. Checkers now validate it before comparing unchanged name/type/value obligations. Wrong kinds still fail.',
            'mps_first_attempt':'Sandboxed Metal discovery failed before query inference; a separately captured authorized local rerun is kept.'}}
    save(output/'review.json',value)
    print(json.dumps({'stage':value['current_stage'],'tt_answer_unchanged':value['tt_answer_unchanged'],
        'A':counts,'B':lexical,'full_semantic_transfer_verified':False}))


if __name__=='__main__':main()
