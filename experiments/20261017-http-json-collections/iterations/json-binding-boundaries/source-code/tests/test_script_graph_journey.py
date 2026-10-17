"""A manually enumerated two-service graph with browser response state.

This is a source fixture, not evidence of a full real application benchmark.
The Java programs are parsed; neither a JVM nor the target services are run.
"""
import json
import pytest
from analyzer.contracts import ContractGrounder, ContractIndex
from analyzer.engine import Engine
from analyzer.frontend import Frontend
from analyzer.project import Project
from analyzer.state import ScenarioState
from builders import build


@pytest.mark.parametrize('enabled,branch',[(True,'approved'),(False,'denied')])
def test_script_response_reaches_remote_branch_and_full_source_graph(tmp_path,enabled,branch):
    project,db,ids=build(tmp_path,{
        'Shop.java':'''class CatalogApi {
          @GetMapping("/catalog") List<Item> catalog(){
            Item item=new Item();item.id="part-one";return Arrays.asList(item);}}
        class CheckoutApi {@Autowired Bridge bridge;
          @PostMapping("/checkout") String checkout(@RequestBody Input input){return bridge.submit(input.selectedId);}}
        class Bridge {RestTemplate rest;
          String submit(String id){return rest.postForObject("http://stock/stock/"+id,"reserve",String.class);}}
        class Input {String selectedId;}
        ''',
        'Stock.java':'''class StockApi {@Autowired Store store;
          @PostMapping("/stock/{id}") String reserve(@PathVariable String id){
            Item row=store.findById(id).orElseThrow();
            if(row.quantity>0){return approved();}return denied();}
          String approved(){return "yes";}String denied(){return "no";}}
        @Entity @Table(name="parts") class Item {@Id String id;int quantity;}
        interface Store extends JpaRepository<Item,String>{}
        '''},rows={'parts':[{'id':'part-one','quantity':int(enabled)}]})
    skeleton=project.skeleton
    for unit in ('shop','stock'):
        skeleton['nodes']['module:'+unit]={'kind':'module','name':unit,'deployment_units':[unit]}
    for node in skeleton['nodes'].values():
        if node.get('file') in ('Shop.java','Stock.java'):
            node['module']='shop' if node['file']=='Shop.java' else 'stock'
    (tmp_path/'skeleton.json').write_text(json.dumps(skeleton))
    project=Project(tmp_path/'skeleton.json',tmp_path)
    (tmp_path/'page.html').write_text('<script src="ui.js"></script>')
    (tmp_path/'ui.js').write_text('''var cachedItems=null;
      function load(){$.ajax({url:"/catalog",type:"GET",success:function(reply){cachedItems=reply;}});}
      function checkout(){$.ajax({url:"/checkout",type:"POST",data:{selectedId:cachedItems[0].id}});}''')
    # Fixed reference from the source bodies, before running the analyzer.
    first={('', 'executes',ids['CatalogApi.catalog'])}
    methods=['CheckoutApi.checkout','Bridge.submit','StockApi.reserve','StockApi.'+branch]
    second={('', 'executes',ids[name]) for name in methods}
    second|={(ids['CheckoutApi.checkout'],'calls',ids['Bridge.submit']),
             (ids['Bridge.submit'],'remote',ids['StockApi.reserve']),
             (ids['StockApi.reserve'],'calls',ids['StockApi.'+branch]),
             (ids['StockApi.reserve'],'data','res:table:service.parts')}
    frontend,state=Frontend(project),ScenarioState(db)
    site=next(s for s in frontend.sites.values() if s['handlers']==[ids['CatalogApi.catalog']])
    frontend.enter(site,state)
    read=Engine(project,state)
    result=read.run(ids['CatalogApi.catalog'],{})
    frontend.apply_response(site,result,state)
    assert read.edges==first
    index=ContractIndex(project,frontend)
    contract=next(c for c in index.contracts.values() if c['entry']==ids['CheckoutApi.checkout'])
    proposal=ContractGrounder(project,frontend,index,None,{'facts':{}})._bind('Checkout item',state,contract,1)
    assert proposal['params']=={'selectedId':'part-one'}
    write=Engine(project,proposal['state'])
    result=write.run(ids['CheckoutApi.checkout'],proposal['params'])
    assert result==('yes' if enabled else 'no')
    assert write.edges==second
