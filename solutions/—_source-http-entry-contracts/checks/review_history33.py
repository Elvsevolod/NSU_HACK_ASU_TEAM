"""Immutable stage deltas and actual before/after receipts for E15–E21."""
import argparse
import difflib
import hashlib
import json
import re
from pathlib import Path

V=Path(__file__).resolve().parents[1]
STAGES=['E14-builder-constructor-selection','E15-inline-json-body','E16-json-wire-ownership',
    'E17-source-history-choice','E18-history-origin-chain','E19-selected-response-origin',
    'E20-response-only-history','E21-history-choice-guards']
GATES=['inline-json-body-full-02','json-wire-ownership-full','history-request-choice-full',
    'history-origin-chain-full','history-selected-response-full','history-result-only-full',
    'history-choice-guards-full','history-choice-guards-checker','history-choice-guards-integration-command']
BEFORE=['history-request-choice-before-03','history-origin-chain-before','history-origin-missing-producer-before',
    'history-selected-response-before-02','history-selected-unknown-reference-before',
    'history-result-only-before-02','history-choice-guards-before']


def read(path):return json.loads(path.read_text())
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(exist_ok=False)
    stages={};patches=[]
    for name in STAGES:
        root=V/'development/stages'/name;manifest=read(root/'code-sha256.json')
        assert all(sha(root/'code'/file)==value for file,value in manifest.items())
        stages[name]=read(V/'benchmark/stages'/name/'summary.json')
    for old,new in zip(STAGES,STAGES[1:]):
        before=V/'development/stages'/old/'code';after=V/'development/stages'/new/'code';diff=[];changed=[]
        for file in sorted({p.relative_to(root) for root in (before,after) for p in root.rglob('*') if p.is_file()}):
            b=(before/file).read_text() if (before/file).exists() else '';n=(after/file).read_text() if (after/file).exists() else ''
            if b==n:continue
            changed.append(str(file));diff.extend(difflib.unified_diff(b.splitlines(True),n.splitlines(True),fromfile=old+'/'+str(file),tofile=new+'/'+str(file)))
        path=a.output/(old.split('-')[0]+'-to-'+new.split('-')[0]+'.patch');path.write_text(''.join(diff))
        patches.append({'from':old,'to':new,'files':changed,'patch':path.name,'sha256':sha(path)})
    gates={}
    for name in GATES+BEFORE:
        root=V/'benchmark'/name;run=read(root/'run.json');stdout=(root/'stdout.txt').read_text()
        gates[name]={key:run[key] for key in ('command','cwd','python','returncode','seconds','timed_out')}
        gates[name].update(summary=re.findall(r'\d+ (?:failed|passed)',stdout)[-2:],stdout_sha256=sha(root/'stdout.txt'),stderr_sha256=sha(root/'stderr.txt'))
    result={'current_stage':STAGES[-1],'stages':stages,'patches':patches,'gates':gates,
        'all_eight_tt_answers_unchanged':len({s['submission_sha256'] for s in stages.values()})==1,
        'semantic_model_review':'development/semantic-model-review-e20/review.json',
        'source_oracles_changed':False,'full_semantic_transfer_verified':False,'goal_status':'active',
        'known_test_spec_corrections':['Explicit id=9 must retain its literal producer, not refuse because history id=7 exists.',
            'The second ambiguity endpoint uses a mirror prefix before the same entity, so both source paths really bind the same result identity.',
            'A foreign selected-object type can be ignored when the complete actual response already provides a valid identity.',
            'E20 deliberately replaces selected/parameter-derived ID bookkeeping with an actual response field; complete unknown-metadata digest still refuses. Historical tests and snapshots are retained.'],
        'new_known_false_accept_controls':'E21 rejects a multi-entity compound action and reports an illegal literal GET body after lexical refusal instead of throwing.',
        'default_model':'experiment_rejected','targets_started':False}
    assert result['all_eight_tt_answers_unchanged']
    (a.output/'review.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'stage':STAGES[-1],'patches':len(patches),'all_eight_answers_unchanged':True}))


if __name__=='__main__':main()
