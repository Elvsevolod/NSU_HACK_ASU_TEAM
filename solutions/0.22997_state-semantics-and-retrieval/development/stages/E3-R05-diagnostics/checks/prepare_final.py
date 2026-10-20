"""Freeze accepted measured candidate into the solution root, without changing code."""
import argparse,hashlib,json,platform,sys,shutil,os,importlib.metadata
from pathlib import Path
V=Path(__file__).resolve().parents[1]


def read(path):return json.loads(path.read_text())
def sha(path):
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def main():
    p=argparse.ArgumentParser();p.add_argument('--stage',required=True);args=p.parse_args()
    stage=V/'benchmark/stages'/args.stage;code=read(V/'development/stages'/args.stage/'code-sha256.json')
    assert all(sha(V/'code'/n)==digest for n,digest in code.items())
    target=V/'benchmark/final';assert not target.exists();shutil.copytree(stage,target)
    shutil.copy2(V/'development/stages'/args.stage/'code-sha256.json',target/'code-sha256.json')
    assert not (V/'submission.json').exists();shutil.copy2(stage/'submission.json',V/'submission.json')
    meta={'solution':31,'parent':30,'stage':args.stage,'submission_sha256':sha(V/'submission.json'),
        'input_manifest':'development/input-sha256.json','code_manifest':'benchmark/final/code-sha256.json',
        'path_limit':4,'constraints':True,'graph_policy':'observed-union','site_score':None,
        'environment':{'python':platform.python_version(),'platform':platform.platform(),'logical_cpu_count':os.cpu_count(),'processor_reported':platform.processor(),
            'packages':{n:importlib.metadata.version(n) for n in ('tree-sitter','tree-sitter-java','tree-sitter-javascript','html5lib','pytest','bcrypt','webencodings','six')}},
        'target_applications_started':False,'model_calls':0,'external_llm_api_calls':0,'os_cache_cleared':False}
    (target/'metadata.json').write_text(json.dumps(meta,indent=2)+'\n')
    old=read(V/'development/stages/G16-candidate-final/code-sha256.json')
    delta=[n for n in set(old)|set(code) if old.get(n)!=code.get(n)]
    assert set(delta)=={'analyzer/portable.py','analyzer/reporting.py','tests/test_reporting_measurements.py'}
    prepared={'passed':True,'prepared_run':'benchmark/repeated-analysis-final.json','prepared_code_snapshot':'development/stages/G16-candidate-final',
        'accepted_code_snapshot':'development/stages/'+args.stage,'changed_files':sorted(delta),
        'reason':'Only report-write fast path and its tests changed. Prepared runner calls analyze and unchanged finite_report; it never calls portable.main or dump_report. Exact packaged replay separately checks final code.',
        'analysis_engine_and_prepared_runner_unchanged':True}
    (V/'benchmark/prepared-report-only-delta.json').write_text(json.dumps(prepared,indent=2)+'\n')
    timings={stage:read(V/'benchmark/stages'/stage/'analysis-report-timings.json') for stage in ('G16-parent30-paired','G16-candidate-final',args.stage)}
    result={'environment':meta['environment'],'same_inputs_and_flags':True,'phase_runs':timings,
        'prepared':read(V/'benchmark/repeated-analysis-final.json'),'local_report_pair':read(V/'benchmark/report-phase-profile/results.json'),
        'observed_limitations':['One serial paired environment; background desktop/OS cache are uncontrolled.','Two prepared repetitions, not a distribution or SLA.','Parent and candidate compute different observed graphs and diagnostic states; no equal-work speedup claim.','Full reporting is larger and RSS higher; prepared timings exclude report writing.'],
        'source_index_constructions_per_full_run':1,'model_calls':0,'external_llm_api_calls':0}
    (V/'benchmark/cost-comparison.json').write_text(json.dumps(result,indent=2)+'\n')
    requirements={'solution':31,'source_prompt':'development/inputs/codex_overnight_implementation_prompt.txt',
        'review':'development/inputs/solution_30_followup_review.md','goal_queue':'development/overnight-state.json',
        'accepted_stage':args.stage,'scope':'Python static Java/Spring scenario analysis with ready skeleton; explicit bounded framework contracts.',
        'declared_exclusions':['DeepSeek','external LLM APIs','downloaded models','target/JVM/service execution','scenario/business hardcoding','changes to previous variants/original inputs']}
    (V/'development/requirements.json').write_text(json.dumps(requirements,indent=2)+'\n')
    print(json.dumps(meta))


if __name__=='__main__':main()
