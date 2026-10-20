import sys,tempfile,json
from pathlib import Path
V=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(V/'code'),str(V/'code/tests')]
from builders import build
from analyzer.paths import run_paths
from analyzer.state import ScenarioState
from analyzer.frontend import Frontend
from analyzer.contracts import ContractIndex,ContractGrounder
from analyzer.request import grounded_request,BoundParameters
source="""import org.springframework.web.bind.annotation.*;import org.springframework.http.ResponseEntity;
import org.springframework.boot.autoconfigure.SpringBootApplication;
@SpringBootApplication class App{}
class Parcel{public Long id=7L;}
@RestController class ParcelController{
@PostMapping(\"/parcels\") ResponseEntity<Parcel> create(@RequestBody Parcel input){return ResponseEntity.status(500).body(new Parcel());}
@GetMapping(\"/parcels/{id}\") Parcel getById(@PathVariable Long id){return null;}}"""
with tempfile.TemporaryDirectory() as folder:
 p,db,ids=build(folder,{'Api.java':source});params={'input':{}}
 request=grounded_request(p,ids['ParcelController.create'],params,{})
 paths=run_paths(p,ScenarioState(db),ids['ParcelController.create'],BoundParameters(params,request),limit=4)
 assert len(paths)==1
 out=paths[0];state=out['state'];engine=out['engine']
 state.history.append({'step':1,'action':'Create parcel','entry':ids['ParcelController.create'],
  'parameters':params,'result':out['result'],'selected_objects':[],'created_objects':[],
  'outcome':engine.outcome,'exploration':out['exploration']})
 f=Frontend(p);g=ContractGrounder(p,f,ContractIndex(p,f),None,{'facts':{},'unresolved':[]})
 proposals,detail=g.step('Read the new parcel',state)
 success=[x for x in proposals if x['bindings'].get('id',{}).get('source')=='history' and x['bindings']['id'].get('resolved')]
 print(json.dumps({'producer_outcome':engine.outcome,'producer_complete':out['exploration']['complete'],
  'producer_result':out['result'],'successfully_history_bound_after_failure':len(success),
  'bindings':[x['bindings'] for x in proposals]},default=str))
 assert not success,'Failed HTTP response must not supply a successful new-object producer'
