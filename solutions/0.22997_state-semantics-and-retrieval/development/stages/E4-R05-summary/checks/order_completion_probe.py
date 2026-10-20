"""Diagnostic-only isolated order/completion counters; not a product scheduler."""
import argparse,difflib,inspect,json,sys,time
from collections import Counter
from pathlib import Path
from copy import deepcopy
V=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(V/'code'),str(V/'code/tests')]
from analyzer.paths import run_paths
from analyzer.state import ScenarioState,U
from analyzer.native_storage import JavaList
from analyzer.__main__ import serial
from builders import build


def isolated_runner():
    original=inspect.getsource(run_paths);source=original
    source=source.replace('completion_splits=0',"completion_splits={'order':0,'completion':0}")
    source=source.replace('except AlternativeRequired as branch:',"except AlternativeRequired as branch:\n            category='order' if 'unordered-' in branch.key else 'completion'")
    source=source.replace('except CompletionRequired as completion:',"except CompletionRequired as completion:\n                category='order' if 'unordered-' in completion.key else 'completion'")
    source=source.replace('completion_splits+len','completion_splits[category]+len').replace('completion_splits+=len','completion_splits[category]+=len')
    source=source.replace('completion_splits<completion_budget','min(completion_splits.values())<completion_budget')
    source=source.replace('    return completed','    return completed,completion_splits')
    namespace=dict(run_paths.__globals__);exec(compile(source,'<checker-only-counter-isolation>','exec'),namespace)
    return namespace['run_paths'],original,source


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();assert not a.output.exists();a.output.mkdir(parents=True)
    isolated,old,new=isolated_runner();(a.output/'counter-only.patch').write_text(''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='default/run_paths',tofile='diagnostic/separate-counters')))
    rows={}
    template='''import java.util.*;import jakarta.persistence.*;import org.springframework.data.jpa.repository.JpaRepository;
      @Entity @Table(name="markers")class Marker{@Id String id;String text;}
      interface Store extends JpaRepository<Marker,String>{Optional<Marker> findById(String id);}
      class Api{Store store;Object entry(boolean finish,List<String> visits){
        Marker m=store.findById("anchor").orElseThrow();
        Set<String> keys=new HashSet<>(Arrays.asList("A","B","C"));Map<String,String> values=new HashMap<>();
        for(String key:keys){values.put(key,mark(key,visits));}
        if(finish)return read(values);throw new IllegalStateException();}
        String read(Map<String,String> values){return values.get("B");}
        String mark(String key,List<String> visits){MODE return key;}}'''
    for mode,body in [('commuting',''),('order-effects','visits.add(key);'),('throwing','visits.add(key);if(key.equals("B"))throw new IllegalArgumentException();')]:
        project,db,ids=build(a.output/mode,{'Api.java':template.replace('MODE',body)},rows={'markers':[{'id':'anchor','text':'unchanged'}]})
        variants={}
        for label,runner in [('shared-default',run_paths),('isolated-counters',isolated)]:
            started=time.perf_counter();paths=runner(project,ScenarioState(db),ids['Api.entry'],{'finish':U,'visits':JavaList()},limit=4)
            counts=None
            if isinstance(paths,tuple):paths,counts=paths
            observations=[]
            for path in paths:
                e=path['engine'];assert e.state.database.unknown_tables==set();assert e.state.database.tables==db.tables
                observations.append({'outcome':e.outcome,'result':path['result'],'visits':e.params['visits'],'edges':sorted(e.edges),
                    'conditions':e.conditions,'decisions':path['decisions'],'warnings':sorted(e.warnings)})
            variants[label]={'seconds':time.perf_counter()-started,'outcomes':dict(Counter(x['outcome'] for x in observations)),
                'counter_totals':counts,'observations':observations,'known_read_preserved_database':True}
        rows[mode]=variants
    result={'schema':'completion-budget-isolation/1','production_default_changed':False,
      'counter_contract':'Each category gets the original reserve max(8,limit); this diagnoses coupling and is not a proven optimization or quality fix.',
      'cases':rows,'targets_started':False,'external_llm_api_calls':0}
    (a.output/'results.json').write_text(json.dumps(result,default=serial,indent=2)+'\n')
    print(json.dumps({mode:{key:value['outcomes'] for key,value in variants.items()} for mode,variants in rows.items()}))


if __name__=='__main__':main()
