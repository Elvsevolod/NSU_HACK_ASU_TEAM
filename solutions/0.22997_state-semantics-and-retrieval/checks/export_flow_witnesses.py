"""Export source-owned transitions. Never inject a response ID or login token."""
import argparse,json,sys
from datetime import datetime
from pathlib import Path
V=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(V/'code'),str(V/'code/tests')]
from analyzer.__main__ import analyze,serial
from analyzer.state import ScenarioState
from analyzer.paths import run_paths
from analyzer.frontend import Frontend
from analyzer.contracts import ContractIndex,ContractGrounder,read_static_context
from analyzer.engine import Engine
from analyzer.request import Request
from evidence import capture,chain,heap
from test_inventory_collection_journey import fixture as inventory
from test_angular_legacy_session import fixture as session,attach,UI,JQUERY_UI
from test_actor_credentials_flow import fixture as actors


def nl(p,db,actions,context):
    f=Frontend(p);heaps=[]
    def observed_paths(*args,**kwargs):
        rows=run_paths(*args,**kwargs);heaps.extend(heap(row['state']) for row in rows);return rows
    _,trace=analyze(p,f,ContractIndex(p,f),None,db,context,
        {'id':'witness','steps':[{'n':n,'action':action} for n,action in enumerate(actions,1)]},
        path_limit=4,grounder_type=ContractGrounder,path_runner=observed_paths)
    rows=[a for step in trace['steps'] for a in step['alternatives']]
    assert len(rows)==len(heaps)
    for row,value in zip(rows,heaps):row['heap_after']={'phase':'backend return, browser callback effects in state_after','graph':value}
    return trace,rows


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    assert not args.output.exists();args.output.mkdir(parents=True);chains=[]
    p,db,ids=inventory(args.output/'inputs/inventory');frontier=[(ScenarioState(db),None)];rows=[]
    for n,(entry,method,url) in enumerate([('gateway.InventoryGateway.listProducts','GET','/inventory'),
        ('gateway.InventoryGateway.reserveProduct','POST','/inventory/reserve'),('gateway.InventoryGateway.listProducts','GET','/inventory')],1):
        following=[]
        for state,chosen in frontier:
            request=Request.http('gateway',method,url,body={'id':chosen['id'],'revision':chosen['revision']}) if n==2 else Request.http('gateway',method,url)
            for path in run_paths(p,state,ids[entry],request,limit=4):
                e=path['engine'];result=path['result']
                rows.append({'n':n,**capture(e,request,result),'decisions':path['decisions'],'exploration':path['exploration']})
                assert e.outcome=='returned'
                following.append((e.state,result[1] if n==1 else chosen))
        frontier=following
    (args.output/'inventory-explicit.json').write_text(json.dumps(rows,default=serial,indent=2)+'\n')
    chains.append(chain(rows,'inventory/explicit'))
    trace,rows=nl(p,db,['List products','Reserve second product','List products'],{'facts':{},'unresolved':[]})
    (args.output/'inventory-nl.json').write_text(json.dumps(trace,default=serial,indent=2)+'\n');chains.append(chain(rows,'inventory/NL'))
    for name,ui in [('angular',UI),('jquery',JQUERY_UI)]:
        root=args.output/'inputs'/name;p,db,ids=session(root);attach(root,ui)
        trace,rows=nl(p,db,['As alice, login name "alice" password "secret"','As alice, read protected'],
                      {'facts':{},'unresolved':[],'clock':datetime(2026,10,18)})
        (args.output/(name+'.json')).write_text(json.dumps(trace,default=serial,indent=2)+'\n');chains.append(chain(rows,name+'/source-token'))
    root=args.output/'inputs/two-actors';root.mkdir(parents=True);p,db,_=actors(root)
    context=read_static_context({'accounts':{'alice':{'username':'alice','password':'secret'},'bob':{'username':'bob','password':'bravo'}},
        'date':'System clock 18 October 2026'})
    trace,rows=nl(p,db,['Log in as alice with username and password','As alice, read protected',
        'Log in as bob with username and password','As bob, read protected','As alice, read protected'],context)
    (args.output/'two-actors.json').write_text(json.dumps(trace,default=serial,indent=2)+'\n');chains.append(chain(rows,'two-actors/source-tokens-and-403'))
    (args.output/'witnesses.json').write_text(json.dumps({'schema':'producer-consumer/1','chains':chains,
        'oracle_available_to_inference':False,'manual_token_or_id_insertion':False,'targets_started':False},default=serial,indent=2)+'\n')


if __name__=='__main__':main()
