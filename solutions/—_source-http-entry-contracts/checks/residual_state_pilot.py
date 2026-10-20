"""Opt-in G06 experiment at completed application-call boundaries only.

This is not imported by inference and does not replace paths.py. It retains all
incoming observation prefixes when reusing a suffix from an equivalent state.
There is no suspended Java frame, NL history binding or transaction in this
small experiment; those exclusions prevent extrapolating it to TT continuations.
"""
import argparse
from copy import deepcopy
from datetime import datetime
import hashlib
import json
from pathlib import Path
import resource
import sys
import time

VARIANT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(VARIANT/'code'),str(VARIANT/'code/tests')]
from analyzer.engine import Engine
from analyzer.heap_join import clone_execution,owned_objects
from analyzer.context_key import fingerprint
from analyzer.state import ScenarioState
from builders import build

SOURCE='''import java.util.*;import org.springframework.stereotype.Component;
import javax.annotation.PostConstruct;
import org.springframework.beans.factory.annotation.Autowired;
@Component class Cache {Map<String,List<String>> groups=new HashMap<>();
 Set<String> values=new HashSet<>();Set<String> alias;int counter;
 @PostConstruct void init(){groups.put("L",Arrays.asList("A"));groups.put("M",Arrays.asList("B"));
  groups.put("R",Arrays.asList("C"));values.add("A");values.add("B");values.add("C");}
 void apply(String key){values.removeAll(groups.get(key));}
 Set<String> read(){return values;}}
@Component class Api {@Autowired Cache cache;void apply(String key){cache.apply(key);}Set<String> read(){return cache.read();}}'''


def key_for(state,remaining,source_hash,completion='normal',external_roots=()):
    database={'tables':list(state.database.tables.raw_items()),
              'unknown':sorted(state.database.unknown_tables),'schemas':state.database.schemas}
    roots={'program_point':'between completed apply calls','remaining':sorted(remaining),
           'source_namespace':source_hash,'completion':completion,'active_request_frame':None,
           'state':{k:v for k,v in state.__dict__.items() if k!='database'},
           'database':database,'external_roots':external_roots}
    metadata=[{name:getattr(obj,name) for name in
               ('java_type','declared_type','wire_fields','origin_type','order_known','order',
                'mutation_version','uncertain_versions','flags','used') if hasattr(obj,name)}
              for obj in owned_objects(roots)]
    value=fingerprint((roots,metadata))
    def complete(item):
        return item!=('context-budget',) and (not isinstance(item,tuple) or all(complete(v) for v in item))
    if not complete(value):return None
    return hashlib.sha256(json.dumps(value,sort_keys=True,default=str).encode()).hexdigest()


def prepare(root,mode='commuting'):
    body={'commuting':'values.removeAll(groups.get(key));',
          'order-dependent':'counter++;if(counter%2==1){values.removeAll(groups.get(key));}',
          'datastore-effect':'values.removeAll(groups.get(key));',
          'throwing':'values.removeAll(groups.get(key));throw new IllegalStateException();'}[mode]
    source=SOURCE.replace('values.removeAll(groups.get(key));',body)
    if mode=='datastore-effect':
        source=source.replace('@Component class Cache {',
            '@Entity @Table(name="control") class Revision{@Id public String id;public int revision;}'
            'interface Controls extends JpaRepository<Revision,String>{'
            'Optional<Revision> findById(String id);Revision save(Revision row);}@Component class Cache {')
        source=source.replace('import javax.annotation.PostConstruct;',
                              'import javax.annotation.PostConstruct;import jakarta.persistence.*;import org.springframework.data.jpa.repository.JpaRepository;')
        source=source.replace('@Component class Api {','@Component class Api {@Autowired Controls controls;')
        source=source.replace('void apply(String key){cache.apply(key);}',
            'void apply(String key){Revision row=controls.findById("one").get();row.revision++;controls.save(row);cache.apply(key);}')
    project,db,ids=build(root,{'Api.java':source},rows={'control':[{'id':'one','revision':1}]})
    engine=Engine(project,ScenarioState(db,{'clock':datetime(2026,10,19)}))
    assert sorted(engine.run(ids['Api.read'],{}))==['A','B','C']
    return project,engine.state,ids,hashlib.sha256(source.encode()).hexdigest()


def run(project,state,ids,source_hash,memoized):
    stats={'engine_calls':0,'memo_hits':0,'unique_states':0,'uncacheable_states':0}
    memo={};seen=set()
    def solve(current,remaining):
        signature=key_for(current,remaining,source_hash)
        if signature is None:stats['uncacheable_states']+=1
        else:seen.add(signature)
        if memoized and signature is not None and signature in memo:
            stats['memo_hits']+=1
            return deepcopy(memo[signature])
        if not remaining:
            result=[{'order':[],'state':current,'observations':[]}]
        else:
            result=[]
            for group in remaining:
                (following,),_=clone_execution(current)
                engine=Engine(project,following)
                value=engine.run(ids['Api.apply'],{'key':group});stats['engine_calls']+=1
                observation={'input':group,'result':value,'outcome':engine.outcome,
                    'edges':sorted(engine.edges),'events':deepcopy(engine.events),
                    'conditions':deepcopy(engine.conditions),'effects':deepcopy(engine.effect_events),
                    'data_operations':deepcopy(engine.data_operations)}
                if engine.outcome!='returned':
                    result.append({'order':[group],'state':engine.state,'observations':[observation]})
                    continue
                for suffix in solve(engine.state,tuple(x for x in remaining if x!=group)):
                    result.append({'order':[group,*suffix['order']],'state':suffix['state'],
                                   'observations':[observation,*suffix['observations']]})
        if memoized and signature is not None:memo[signature]=deepcopy(result)
        return result
    started=time.perf_counter();outcomes=solve(state,('L','M','R'))
    stats.update(seconds=time.perf_counter()-started,unique_states=len(seen))
    exported=[]
    for row in outcomes:
        reader=Engine(project,row['state']);values=reader.run(ids['Api.read'],{})
        exported.append({'order':row['order'],'observations':row['observations'],
                         'final_values':sorted(values),'final_signature':key_for(reader.state,(),source_hash),
                         'final_database':reader.state.snapshot(full=True)['tables']})
    return sorted(exported,key=lambda row:row['order']),stats


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    args.output.mkdir(parents=True)
    outcomes={}
    for mode in ('commuting','order-dependent','datastore-effect','throwing'):
        project,state,ids,digest=prepare(args.output/mode,mode)
        reference,slow=run(project,state,ids,digest,False)
        candidate,fast=run(project,state,ids,digest,True)
        assert reference==candidate,(mode,'semantic/provenance mismatch')
        if mode=='datastore-effect':
            assert all(row['final_database']['service.control'][0]['revision']==4 for row in candidate)
            assert all(any(e[1]=='data' for step in row['observations'] for e in step['edges']) for row in candidate)
        outcomes[mode]={'semantic_equal':True,'paths':len(reference),'reference':slow,'memoized':fast,
                        'observations':candidate,'source_sha256':digest}
    result={'schema':'residual-state-pilot/1','passed':True,'cases':outcomes,
            'product_default':'rejected; not integrated into paths.py',
            'scope':'Only completed independent calls with all prefixes retained; no suspended Java frames, source iterators, active transactions or NL producer binding are optimized.',
            'TT_frontier':'Actual Basic242 certification refuses unknown route stations. A suffix cache at this boundary does not repair that producer loss; no TT optimized run is claimed.',
            'relations':'All four edge sets compared exactly. A source repository read/save case validates data effects; remote is empty and is not positive RPC validation.',
            'targets_started':False,'external_llm_api_calls':0}
    raw=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    result['process_peak_rss']={'raw':raw,'unit':'bytes' if sys.platform=='darwin' else 'KiB' if sys.platform.startswith('linux') else 'unknown',
        'bytes':raw if sys.platform=='darwin' else raw*1024 if sys.platform.startswith('linux') else None,
        'scope':'Whole pilot process; not an isolated per-mode peak'}
    (args.output/'pilot.json').write_text(json.dumps(result,default=str,indent=2)+'\n')
    print(json.dumps({mode:{'paths':row['paths'],'reference_calls':row['reference']['engine_calls'],
                           'memoized_calls':row['memoized']['engine_calls'],'hits':row['memoized']['memo_hits']}
                      for mode,row in outcomes.items()}))


if __name__=='__main__':main()
