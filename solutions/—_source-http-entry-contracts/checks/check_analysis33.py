"""Extract every member, validate code/candidate/input hashes, replay bundled inputs."""
import argparse,hashlib,json,os,subprocess,sys,time,zipfile
from pathlib import Path
from archive_support import verified_manifest


def sha(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def main():
    p=argparse.ArgumentParser()
    for arg in ('archive','extracted','output'):p.add_argument('--'+arg,type=Path,required=True)
    p.add_argument('--candidate',default='solution.zip');p.add_argument('--metadata',default='benchmark/candidate-metadata.json')
    a=p.parse_args();a.archive=a.archive.resolve();a.extracted=a.extracted.resolve();a.output=a.output.resolve()
    assert Path(a.candidate).name==a.candidate
    assert not Path(a.metadata).is_absolute() and '..' not in Path(a.metadata).parts
    a.output.mkdir(parents=True,exist_ok=False);assert not a.extracted.exists()
    started=time.perf_counter();result={'passed':False,'archive_sha256':sha(a.archive),'targets_started':False,'model_forward_required':False}
    with zipfile.ZipFile(a.archive) as z:
        manifest=verified_manifest(z,'MANIFEST.json');assert z.testzip() is None
        assert {'solution_33/code/offline_run.py','solution_33/'+a.candidate,'solution_33/'+a.metadata,
            'inputs/tt-challenge/skeleton/trainticket.json.gz','inputs/tt-challenge/platform/evaluate_golden.py'}<=set(manifest)
        z.extractall(a.extracted)
    assert all(sha(a.extracted/name)==digest for name,digest in manifest.items())
    v=a.extracted/'solution_33';challenge=a.extracted/'inputs/tt-challenge'
    metadata=json.loads((v/a.metadata).read_text())
    assert {p.relative_to(v/'code').as_posix() for p in (v/'code').rglob('*') if p.is_file()}==set(metadata['code_sha256'])
    assert all(sha(v/'code'/name)==digest for name,digest in metadata['code_sha256'].items())
    with zipfile.ZipFile(v/a.candidate) as z:
        verified_manifest(z,'benchmark/package-manifest.json')
        assert z.read('benchmark/candidate-metadata.json')==(v/a.metadata).read_bytes()
        assert {name.removeprefix('code/') for name in z.namelist() if name.startswith('code/') and not name.endswith('/')}==set(metadata['code_sha256'])
        assert z.read('submission.json')==(v/'submission.json').read_bytes()
        assert all(z.read('code/'+name)==(v/'code'/name).read_bytes() for name in metadata['code_sha256'])
    result.update(member_hashes_verified=len(manifest),all_files_extracted=True,code_matches_candidate=True,
        candidate=a.candidate,stage=metadata['source_stage'],candidate_sha256=sha(v/a.candidate),submission_sha256=sha(v/'submission.json'))
    commands=[('analyzer',[sys.executable,'-B',str(v/'code/offline_run.py'),'--source',str(challenge/'targets/trainticket'),
        '--skeleton',str(challenge/'skeleton/trainticket.json.gz'),'--context',str(challenge/'context'),'--scenarios',str(challenge/'scenarios'),
        '--output',str(a.output/'submission.json'),'--report',str(a.output/'report.json')]),
        ('metric-controls',[sys.executable,'-B','-m','pytest','-q','-p','no:cacheprovider','checks/tests/test_code_model_metrics33.py']),
        ('evaluation',[sys.executable,'-B',str(challenge/'platform/evaluate_golden.py'),str(challenge/'gold/S0.json'),str(a.output/'submission.json'),'--json']),
        ('format-check',[sys.executable,'-B',str(challenge/'platform/evaluate_golden.py'),'--check',str(challenge/'skeleton/trainticket.json.gz'),str(a.output/'submission.json'),'--json'])]
    if (v/'development/transport-oracle-frozen-v2').is_dir():
        commands.extend([
            ('transport-controls',[sys.executable,'-B','-m','pytest','-q','-p','no:cacheprovider',
                'checks/tests/test_semantic_wire_checker33.py','checks/tests/test_semantic_holdout_checker33.py','checks/tests/test_cart_evaluator_v3.py']),
            ('transport-recheck',[sys.executable,'-B','checks/recheck_transport33.py','--runs','benchmark/semantic-holdout-e14-v1','--output',str(a.output/'transport')])])
    if (v/'benchmark/real-retrieval-evaluation.json').is_file():
        commands.append(('new-retrieval-metrics',[sys.executable,'-B','checks/evaluate_real_retrieval33.py','--mode','evaluate',
            '--dense','benchmark/real-retrieval-coderank-02/predictions.json','--output',str(a.output/'real-retrieval-evaluation.json')]))
    if (v/'development/semantic-model-review-e20/review.json').is_file():
        commands.append(('semantic-model-recheck',[sys.executable,'-B','checks/review_semantic_models33.py',
            '--output',str(a.output/'semantic-model-review')]))
    if (v/'development/stages/E21-history-choice-guards').is_dir():
        commands.extend([
            ('history-and-json-controls',[sys.executable,'-B','-m','pytest','-q','-p','no:cacheprovider',
                'code/tests/test_history_request_choice33.py','code/tests/test_history_agreement32.py','code/tests/test_inline_json_body33.py']),
            ('current-transport-recheck',[sys.executable,'-B','checks/recheck_transport33.py',
                '--runs','benchmark/semantic-holdout-e21-lexical-v1','--output',str(a.output/'current-transport')])])
    runs=[]
    for name,command in commands:
        before=time.perf_counter()
        with (a.output/(name+'.stdout.txt')).open('w') as out,(a.output/(name+'.stderr.txt')).open('w') as err:
            completed=subprocess.run(command,cwd=v,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','PYTHONPATH':str(v/'code')},stdout=out,stderr=err,timeout=600)
        runs.append({'name':name,'command':command,'returncode':completed.returncode,'seconds':time.perf_counter()-before})
    result['runs']=runs
    command_passed=all(r['returncode'] in ((0,3) if r['name'] in ('evaluation','format-check') else (0,)) for r in runs)
    if command_passed:
        evaluation=json.loads((a.output/'evaluation.stdout.txt').read_text())
        fmt=json.loads((a.output/'format-check.stdout.txt').read_text())
        result['fresh_evaluation']={'s0':evaluation['score'],'errors':evaluation['errors'],'warnings':evaluation['warnings']}
        result['fresh_format_check']={'errors':fmt['errors'],'warnings':fmt['warnings']}
        evaluated=evaluation['score']==metadata['s0'] and not any((evaluation['errors'],evaluation['warnings'],fmt['errors'],fmt['warnings']))
        result['all_eight_answers_match']=sha(a.output/'submission.json')==sha(v/'submission.json')
        audit=json.loads((a.output/'report-offline-audit.json').read_text());result['offline_audit']=audit
        result['passed']=evaluated and result['all_eight_answers_match'] and not any(audit[k] for k in ('blocked_network','blocked_processes','blocked_reference_reads'))
        if (a.output/'transport/counts.json').is_file():
            result['transport_checks_reproduced']=json.loads((a.output/'transport/counts.json').read_text())==json.loads((v/'development/transport-checker-e14/counts.json').read_text())
            result['passed'] &= result['transport_checks_reproduced']
        if (a.output/'real-retrieval-evaluation.json').is_file():
            result['new_retrieval_metrics_reproduced']=json.loads((a.output/'real-retrieval-evaluation.json').read_text())==json.loads((v/'benchmark/real-retrieval-evaluation.json').read_text())
            result['passed'] &= result['new_retrieval_metrics_reproduced']
        if (a.output/'semantic-model-review/review.json').is_file():
            result['semantic_model_metrics_reproduced']=json.loads((a.output/'semantic-model-review/review.json').read_text())==json.loads((v/'development/semantic-model-review-e20/review.json').read_text())
            result['passed'] &= result['semantic_model_metrics_reproduced']
        if (a.output/'current-transport/counts.json').is_file():
            result['current_transport_reproduced']=json.loads((a.output/'current-transport/counts.json').read_text())==json.loads((v/'development/transport-checker-e21-lexical/counts.json').read_text())
            result['passed'] &= result['current_transport_reproduced']
    result['seconds']=time.perf_counter()-started
    (a.output/'check.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    a.archive.with_suffix('.check.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(result,ensure_ascii=False));raise SystemExit(0 if result['passed'] else 1)


if __name__=='__main__':main()
