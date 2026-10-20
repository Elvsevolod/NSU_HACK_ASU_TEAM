"""Multi-item independent catalog/warehouse HTTP + NL regression, not a holdout."""
import json
import pytest
from analyzer.project import Project
from analyzer.state import ScenarioState
from analyzer.request import Request
from analyzer.paths import run_paths
from analyzer.frontend import Frontend
from analyzer.contracts import ContractIndex,ContractGrounder
from analyzer.__main__ import analyze
from builders import build

GATEWAY='''import java.util.*;import org.springframework.web.client.RestTemplate;
 class ProductView{public String id;public String category;public int revision;public int quantity;}
 class Category{public String code;}
 class ProductRequest{public String id;public int revision;}
 class InventoryGateway{RestTemplate rest;
  @GetMapping("/inventory") List<ProductView> listProducts(){
   ProductView[] received=rest.getForObject("http://warehouse/products",ProductView[].class);
   List<ProductView> products=new ArrayList<>(Arrays.asList(received));Set<String> codes=new HashSet<>();
   Map<String,List<ProductView>> groups=new HashMap<>();
   for(ProductView product:products){codes.add(product.category);
    if(groups.get(product.category)==null){groups.put(product.category,new ArrayList<>());}groups.get(product.category).add(product);}
   Category[] categories=rest.postForObject("http://catalog/categories",new ArrayList<>(codes),Category[].class);
   Map<String,Category> categoryMap=new HashMap<>();for(Category category:categories){categoryMap.put(category.code,category);}
   for(String code:groups.keySet()){if(categoryMap.get(code)==null){products.removeAll(groups.get(code));}}
   return products;}
  @PostMapping("/inventory/reserve") ProductView reserveProduct(@RequestBody ProductRequest input){
   return rest.postForObject("http://warehouse/products/"+input.id+"/reserve",input,ProductView.class);}}
'''
WAREHOUSE='''import java.util.*;import org.springframework.data.jpa.repository.JpaRepository;import org.springframework.http.*;
 @Entity @Table(name="products")class Product{@Id public String id;public String category;public int revision;public int quantity;}
 class ProductRequest{public String id;public int revision;}
 interface Stock extends JpaRepository<Product,String>{Product findById(String id);Product save(Product product);}
 class StockController{Stock stock;
  @GetMapping("/products") List<Product> listProducts(){return Arrays.asList(stock.findById("SKU7"),stock.findById("SKU8"),stock.findById("SKU9"));}
  @PostMapping("/products/{id}/reserve") ResponseEntity<Product> reserveProduct(@PathVariable String id,@RequestBody ProductRequest input){
   Product product=stock.findById(id);if(product.revision!=input.revision){return new ResponseEntity<Product>(null,HttpStatus.CONFLICT);}
   product.quantity--;product.revision++;stock.save(product);return ResponseEntity.ok(product);}}
'''
CATALOG='''import java.util.*;import org.springframework.data.jpa.repository.JpaRepository;
 @Entity @Table(name="categories")class Category{@Id public String code;}
 interface Categories extends JpaRepository<Category,String>{List<Category> findByCodeIn(List<String> codes);}
 class CategoryController{Categories categories;@PostMapping("/categories")List<Category> lookup(@RequestBody List<String> codes){return categories.findByCodeIn(codes);}}
'''


def fixture(root,gateway=GATEWAY,catalog=CATALOG):
    merged={'project':'inventory','nodes':{},'edges':[]};ids={};databases=[]
    for module,source,rows in [('gateway',gateway,{}),('warehouse',WAREHOUSE,{'products':[
        {'id':'SKU7','category':'hardware','revision':4,'quantity':8},
        {'id':'SKU8','category':'office','revision':5,'quantity':9},
        {'id':'SKU9','category':'hardware','revision':6,'quantity':10}]}),
        ('catalog',catalog,{'categories':[{'code':'hardware'},{'code':'office'}]})]:
        p,db,local=build(root/module,{'Api.java':source},module=module,rows=rows)
        databases.append(db)
        for node in p.skeleton['nodes'].values():
            if node.get('file'):node['file']=module+'/'+node['file']
            for origin in node.get('origin',[]):origin['file']=module+'/'+origin['file']
        merged['nodes'].update(p.skeleton['nodes']);merged['edges'].extend(p.skeleton['edges'])
        ids.update({module+'.'+key:value for key,value in local.items()})
    db=databases[0]
    for other in databases[1:]:
        for key,value in other.tables.raw_items():db.tables[key]=value
    (root/'skeleton.json').write_text(json.dumps(merged))
    (root/'gateway/ui.js').write_text('''new Vue({data:{products:[]},methods:{
      listProducts(){var vm=this;$.ajax({url:"/inventory",type:"GET",success:function(data){vm.products=data;}});},
      reserveProduct(item){$.ajax({url:"/inventory/reserve",type:"POST",contentType:"application/json",data:JSON.stringify({id:item.id,revision:item.revision})});}}});''')
    (root/'gateway/page.html').write_text('''<script src="ui.js"></script><button @click="listProducts">List products</button>
      <div v-for="item in products"><button @click="reserveProduct(item)">Reserve product</button></div>''')
    return Project(root/'skeleton.json',root),db,ids


@pytest.mark.parametrize('limit',[1,4,8])
def test_batch_unique_membership_noop_and_following_http_request(tmp_path,limit):
    p,db,ids=fixture(tmp_path);state=ScenarioState(db)
    paths=run_paths(p,state,ids['gateway.InventoryGateway.listProducts'],Request.http('gateway','GET','/inventory'),limit=limit)
    assert len(paths)==1
    engine=paths[0]['engine'];products=paths[0]['result']
    assert [r['id'] for r in products]==['SKU7','SKU8','SKU9']
    assert not engine.approximate and not engine.state.database.unknown_tables
    batch=next(row for row in engine.request_events if row['entry']==ids['catalog.CategoryController.lookup'])
    codes=batch['bound_arguments'][0]['value']
    assert len(codes)==2 and set(codes)=={'hardware','office'}
    assert any(row.get('model_version')=='native-map-noop/1' for row in engine.effect_events)
    chosen=products[1]
    request=Request.http('gateway','POST','/inventory/reserve',body={'id':chosen['id'],'revision':chosen['revision']})
    written=run_paths(p,engine.state,ids['gateway.InventoryGateway.reserveProduct'],request,limit=limit)
    assert len(written)==1 and written[0]['result']=={'id':'SKU8','category':'office','revision':6,'quantity':8}
    state=written[0]['state']
    assert len(state.database.tables[('warehouse','products')])==3 and not state.database.unknown_tables
    assert state.database.tables[('warehouse','products')][0]['quantity']==8


def test_nl_selects_observed_product_and_rereads_changed_state(tmp_path):
    p,db,ids=fixture(tmp_path);frontend=Frontend(p)
    _,trace=analyze(p,frontend,ContractIndex(p,frontend),None,db,{'facts':{},'unresolved':[],'choice_rules':[]},
        {'id':'inventory','steps':[{'n':1,'action':'List products'},{'n':2,'action':'Reserve second product'},
                                  {'n':3,'action':'List products'}]},path_limit=4,grounder_type=ContractGrounder)
    second=trace['steps'][1]['alternatives']
    assert len(second)==1 and second[0]['entry']==ids['gateway.InventoryGateway.reserveProduct']
    assert second[0]['request']['body']=={'id':'SKU8','revision':5}
    assert second[0]['result']=={'id':'SKU8','category':'office','revision':6,'quantity':8}
    assert trace['steps'][2]['alternatives'][0]['result'][1]==second[0]['result']


def test_missing_category_runs_real_removal_instead_of_noop_summary(tmp_path):
    p,db,ids=fixture(tmp_path);db.tables[('catalog','categories')]=[{'code':'hardware'}]
    paths=run_paths(p,ScenarioState(db),ids['gateway.InventoryGateway.listProducts'],Request.http('gateway','GET','/inventory'),limit=4)
    assert paths and all([r['id'] for r in path['result']]==['SKU7','SKU9'] for path in paths)
    assert all(not any(e.get('model_version')=='native-map-noop/1' for e in path['engine'].effect_events) for path in paths)
    assert all(not path['state'].database.unknown_tables for path in paths)


def test_remote_effect_inside_false_filter_is_not_omitted(tmp_path):
    gateway=GATEWAY.replace('for(String code:groups.keySet()){','for(String code:groups.keySet()){rest.postForObject("http://catalog/audit",code,String.class);')
    catalog=CATALOG+'class Audit{@PostMapping("/audit")String accept(@RequestBody String code){return "seen";}}'
    p,db,ids=fixture(tmp_path,gateway,catalog)
    paths=run_paths(p,ScenarioState(db),ids['gateway.InventoryGateway.listProducts'],Request.http('gateway','GET','/inventory'),limit=4)
    assert paths and all(len(path['result'])==3 for path in paths)
    for path in paths:
        e=path['engine'];assert not any(e.get('model_version')=='native-map-noop/1' for e in e.effect_events)
        assert (ids['gateway.InventoryGateway.listProducts'],'remote',ids['catalog.Audit.accept']) in e.edges
        assert len([r for r in e.request_events if r['entry']==ids['catalog.Audit.accept']])==2


def test_stale_product_revision_refuses_before_save(tmp_path):
    p,db,ids=fixture(tmp_path)
    request=Request.http('warehouse','POST','/products/SKU8/reserve',body={'id':'SKU8','revision':1})
    path=run_paths(p,ScenarioState(db),ids['warehouse.StockController.reserveProduct'],request,limit=4)[0]
    e=path['engine'];assert e.http_responses[-1]['status']==409
    assert [o['operation'] for o in e.data_operations]==['findById']
    assert e.state.database.tables[('warehouse','products')][1]['revision']==5
