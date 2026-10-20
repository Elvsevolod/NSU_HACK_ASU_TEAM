"""Optional local-only contract reranker experiment; never a required backend."""
import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path
import resource
import sys
import time

VARIANT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(VARIANT/'code'),str(VARIANT/'checks')]
from analyzer.project import Project
from analyzer.state import Database
from analyzer.frontend import Frontend
from analyzer.contracts import ContractIndex,ContractGrounder,read_static_context
from analyzer.__main__ import analyze,serial
from compare_public_corpus import edge_set,subset


def validate_choice(value,count):
    if not isinstance(value,dict) or set(value)!={'index'} or type(value['index']) is not int:return None
    return value['index'] if -1<=value['index']<count else None


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--fixtures',type=Path,required=True)
    parser.add_argument('--model',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--cpu',action='store_true');args=parser.parse_args()
    assert not args.output.exists();args.output.mkdir(parents=True)
    from llama_cpp import Llama
    started=time.perf_counter()
    with args.model.open('rb') as stream:digest=hashlib.file_digest(stream,'sha256').hexdigest()
    expected='8cdb57cbb880d313736a9bc4e3d3d2485f145b5e19cf33783746e753e82641fc'
    assert digest==expected,'Previously pinned model integrity mismatch'
    loaded=time.perf_counter();model=Llama(model_path=str(args.model),n_ctx=4096,n_gpu_layers=0 if args.cpu else -1,
        offload_kqv=not args.cpu,op_offload=not args.cpu,n_threads=4,seed=0,verbose=False)
    load_seconds=time.perf_counter()-loaded
    traces=[];cache={}
    class RerankedIndex(ContractIndex):
        references=None
        def rank(self,action,active_page=None,scenario_text=''):
            ranked=super().rank(action,active_page,scenario_text)
            choices=ranked[:6]
            if len(choices)<2:return ranked
            contracts=[]
            for position,(_,_,contract) in enumerate(choices):
                entry=contract['entry']
                contracts.append({'index':position,'method':entry,'parameters':self.project.http_parameters(entry),
                    'body_fields':self.project.request_fields(entry),
                    'routes':[(verb,route) for mid,verb,route in self.project.ix.handlers if mid==entry]})
            payload={'action':action,'contracts':contracts,'typed_history_references':self.references}
            key=json.dumps(payload,sort_keys=True,default=serial)
            if key not in cache:
                call_started=time.perf_counter()
                response=model.create_chat_completion(messages=[{'role':'system','content':
                    'Select the source-derived HTTP contract that implements the action. Select only a provided index. '
                    'Use typed object/collection references when present. Do not invent endpoints, values, state or edges. '
                    'Use -1 to abstain. Reply only with JSON {"index": integer}.'},
                    {'role':'user','content':key}],temperature=0,seed=0,max_tokens=40,
                    response_format={'type':'json_object','schema':{'type':'object','properties':{'index':{'type':'integer','enum':list(range(-1,len(choices)))}},'required':['index'],'additionalProperties':False}})
                raw=response['choices'][0]['message']['content']
                try:selected=validate_choice(json.loads(raw),len(choices))
                except (ValueError,TypeError):selected=None
                cache[key]=selected
                traces.append({'input':payload,'raw_output':raw,'validated_index':selected,
                    'seconds':time.perf_counter()-call_started,'usage':response.get('usage'),
                    'fallback':selected is None or selected<0})
                print(json.dumps({'model_call':len(traces),'seconds':traces[-1]['seconds'],'selected':selected}),flush=True)
            selected=cache[key]
            if selected is None or selected<0:return ranked
            chosen=choices[selected]
            return [(ranked[0][0]+1,chosen[1],chosen[2]),*(item for item in ranked if item[1]!=chosen[1])]
    class Grounder(ContractGrounder):
        def step(self,action,state,scenario_text='',prepared_proposal=None):
            self.index.references=[item.get('response_refs') for item in state.history[-2:] if item.get('response_refs')]
            return super().step(action,state,scenario_text,prepared_proposal)
    results=[]
    for fixture in sorted(args.fixtures.iterdir()):
        if not (fixture/'skeleton.json').exists():continue
        project=Project(fixture/'skeleton.json',fixture);frontend=Frontend(project);index=RerankedIndex(project,frontend)
        scenario=json.loads((fixture/'scenarios.json').read_text());database=Database(fixture/'initial.sql')
        block,report=analyze(project,frontend,index,None,database,read_static_context({}),scenario,grounder_type=Grounder)
        oracle=json.loads((fixture/'oracle.json').read_text())
        graph=edge_set(block['edges'])==edge_set(oracle['edges'])
        endpoints=all(observed['alternatives'] and all(a['entry']==wanted['endpoint'] for a in observed['alternatives'])
            for observed,wanted in zip(report['steps'],oracle['steps']))
        states=all(observed['alternatives'] and all(subset(wanted['rows'],a['state_after']['database_rows']) for a in observed['alternatives'])
            for observed,wanted in zip(report['steps'],oracle['steps']))
        outcomes=all(observed['alternatives'] and all(wanted['ignore_result'] or
            (subset(wanted['result'],a['result']) if wanted.get('result_subset') else wanted['result']==a['result']) for a in observed['alternatives'])
            for observed,wanted in zip(report['steps'],oracle['steps']))
        arguments=all(observed['alternatives'] and all(subset(wanted['arguments'],a['parameters']) for a in observed['alternatives'])
            for observed,wanted in zip(report['steps'],oracle['steps']))
        statuses=all(observed['alternatives'] and all(a['responses'] and wanted['status']==a['responses'][-1]['status'] for a in observed['alternatives'])
            for observed,wanted in zip(report['steps'],oracle['steps']))
        results.append({'fixture':fixture.name,'graph_exact':graph,'endpoints_exact':endpoints,'states_exact':states,
            'arguments_exact':arguments,'statuses_exact':statuses,'results_exact':outcomes})
        (args.output/(fixture.name+'.json')).write_text(json.dumps({'block':block,'report':report},default=serial,separators=(',',':'))+'\n')
    report={'model':'Qwen3-4B-Instruct-2507-Q4_K_M','model_sha256':digest,'runtime':'llama-cpp-python/'+importlib.metadata.version('llama-cpp-python'),
        'cpu':args.cpu,'load_seconds':load_seconds,'elapsed_seconds':time.perf_counter()-started,
        'peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'calls':len(traces),
        'generation_seconds':sum(t['seconds'] for t in traces),'traces':traces,'results':results,
        'external_llm_api_calls':0,'deepseek_calls':0,'target_applications_started':False,
        'acceptance':'Adopt only if full endpoint/result/state/edge errors improve at acceptable measured resources; otherwise retain lexical default.'}
    (args.output/'experiment.json').write_text(json.dumps(report,indent=2,default=serial)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('traces',)}))


if __name__=='__main__':main()
