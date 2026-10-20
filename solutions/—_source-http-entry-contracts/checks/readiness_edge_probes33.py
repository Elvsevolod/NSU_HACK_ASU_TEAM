"""Remaining small readiness witnesses; Python source analysis only."""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

V = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(V/'code/tests'))
from builders import build
from analyzer.engine import Engine
from analyzer.native_storage import JavaList
from analyzer.paths import join_states, run_paths
from analyzer.state import ScenarioState, U


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);a=parser.parse_args()
    assert not a.output.exists();a.output.mkdir(parents=True);records=[]
    def observed(name, source, e, result):
        records.append({'case':name,'source_sha256':hashlib.sha256(source.encode()).hexdigest(),
            'result':result,'outcome':e.outcome,'edges':sorted(e.edges),
            'requests':e.request_events,'responses':e.http_responses,
            'data_operations':e.data_operations,'effects':e.effect_events,
            'losses':e.loss_events,'warnings':sorted(e.warnings),
            'unknown_tables':sorted(e.state.database.unknown_tables)})
    with TemporaryDirectory() as directory:
        root=Path(directory)
        source='''import java.util.*; class Api {Object entry(){Arrays.asList(1).stream().forEach(null);return after();}int after(){return 99;}}'''
        p,db,ids=build(root/'null-consumer',{'Api.java':source});e=Engine(p,ScenarioState(db))
        result=e.run(ids['Api.entry'],{})
        assert result is U and e.outcome=='uncaught application exception'
        assert ('','executes',ids['Api.after']) not in e.edges
        observed('nonempty-null-consumer',source,e,result)
        source='''import java.util.*; class Api{Object entry(String input){return Optional.ofNullable(input).isEmpty();}}'''
        p,db,ids=build(root/'unknown-presence',{'Api.java':source});e=Engine(p,ScenarioState(db))
        result=e.run(ids['Api.entry'],{'input':U});assert result is U
        observed('unknown-optional-presence',source,e,result)
        source='''class Api{static int cell=0;int entry(boolean flag){if(flag)cell=1;else cell=2;return cell;}int read(){return cell;}}'''
        p,db,ids=build(root/'static-join',{'Api.java':source})
        paths=run_paths(p,ScenarioState(db),ids['Api.entry'],{'flag':U},limit=4)
        assert {r['result'] for r in paths}=={1,2}
        joined=join_states([r['state'] for r in paths]);e=Engine(p,joined)
        result=e.run(ids['Api.read'],{});assert result is U
        assert Engine(p,ScenarioState(db)).run(ids['Api.read'],{})==0
        observed('joined-static-not-first-branch',source,e,result)
        source='''import java.util.*; import jakarta.persistence.*;
          import org.springframework.beans.factory.annotation.Autowired;
          import org.springframework.data.jpa.repository.JpaRepository;
          class Api{@Autowired Store store;Object entry(List<String> input){
            input.stream().filter(id->{Item row=store.findById(id).get();
              Item alias=row;alias.status="held";store.save(alias);return true;}).toList();return after();}
            int after(){return 99;}}
          @Entity @Table(name="items") class Item{@Id public String id;public String status;}
          interface Store extends JpaRepository<Item,String>{Optional<Item> findById(String id);Item save(Item item);}'''
        p,db,ids=build(root/'unknown-write-filter',{'Api.java':source},rows={'items':[{'id':'A','status':'free'}]})
        for enabled in (False,True):
            values=JavaList();values.opaque=True;e=Engine(p,ScenarioState(db,{'scoped_effect_summary':enabled}))
            result=e.run(ids['Api.entry'],{'input':values})
            assert result is U and e.outcome=='unsupported_semantics boundary'
            assert ('','executes',ids['Api.after']) not in e.edges
            assert not any(x.get('operation')=='save' for x in e.data_operations)
            assert not any(x.get('model_version')=='readonly-native-foreach-stop/1' for x in e.effect_events)
            assert e.state.database.rows(p.nodes['res:table:service.items']) is None
            observed('unknown-filter-alias-write-summary-'+str(enabled),source,e,result)
    (a.output/'results.json').write_text(json.dumps({'passed':True,'cases':records,'targets_started':False},default=str,indent=2)+'\n')
    print(json.dumps({'passed':True,'cases':len(records)}))


if __name__=='__main__':main()
