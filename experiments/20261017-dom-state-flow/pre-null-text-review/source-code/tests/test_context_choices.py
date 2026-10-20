from analyzer.context_choices import choice_rules, default_choices
from analyzer.contracts import read_static_context
from analyzer.state import U
from builders import build


CONTEXT={'choices':'Where a product or warehouse is not further specified, the first one is taken.'}
SOURCE={'Api.java':'''class Api {
  @PostMapping("/orders") String buy(@RequestBody Purchase input){return input.productName;}
} class Purchase {String productName;double productPrice;String warehouseName;String cityName;}
class Product {String productName;double price;}
class Warehouse {String warehouseName;String cityName;List<Product> productList;}
class Catalog {List<Product> localProducts;Map<String,List<Warehouse>> warehouses;}
'''}


def invoke(project, mid, action, history, params=None, context=CONTEXT):
    return default_choices(project,mid,project.request_fields(mid),action,history,choice_rules(context),params or {})


def test_default_rule_is_scoped_to_explicit_nouns_and_keeps_evidence():
    rules=read_static_context(CONTEXT)['choice_rules']
    assert [r['entity'] for r in rules]==[['product'],['warehouse']]
    assert all(r['reference']=='context.choices' and 'first one' in r['quote'] for r in rules)
    assert choice_rules({'other':'The first trip is faster.'})==[]


def test_first_product_price_and_name_come_from_the_same_returned_record(tmp_path):
    project,_,ids=build(tmp_path,SOURCE)
    history=[{'result':[{'__type__':'Product','productName':'Second by spelling','price':29},
                        {'__type__':'Product','productName':'Alpha','price':3}]}]
    got=invoke(project,ids['Api.buy'],'Buy a ticket with product',history)
    assert got['productName'][0]=='Second by spelling' and got['productPrice'][0]==29
    assert '[0]' in got['productPrice'][1]
    assert invoke(project,ids['Api.buy'],'Buy a ticket',history)=={}
    assert invoke(project,ids['Api.buy'],'Buy a ticket with new product',history)=={}
    assert invoke(project,ids['Api.buy'],'Update product name',history)=={}
    assert invoke(project,ids['Api.buy'],'Buy a ticket with product',history,context={})=={}
    assert invoke(project,ids['Api.buy'],'Buy a ticket with second product',history)['productName'][0]=='Alpha'


def test_nested_first_warehouse_and_product_stay_with_named_map_key(tmp_path):
    project,_,ids=build(tmp_path,SOURCE)
    warehouse=lambda name,city,product: {'__type__':'Warehouse','warehouseName':name,'cityName':city,
       'productList':[{'__type__':'Product','productName':product,'price':19},
                      {'__type__':'Product','productName':'Other','price':5}]}
    history=[{'action':'Browse warehouses at North Port city','result':{'__type__':'Catalog',
      'localProducts':[{'__type__':'Product','productName':'Local','price':1}],
      'warehouses':{'__map__':{'South Pier':[warehouse('A','South Pier','Wrong')],
                             'North Port':[warehouse('B','North Port','Chosen'),warehouse('C','North Port','Later')]}}}}]
    got=invoke(project,ids['Api.buy'],'Buy a ticket with product from a warehouse',history)
    assert {key:result[0] for key,result in got.items()}=={
      'productName':'Chosen','productPrice':19,'warehouseName':'B','cityName':'North Port'}
    history[0]['action']='Browse warehouses'
    got=invoke(project,ids['Api.buy'],'Buy a ticket with product from a warehouse',history)
    assert 'warehouseName' not in got # no invented HashMap order
    assert invoke(project,ids['Api.buy'],'Buy a ticket with local product',history)['productName'][0]=='Local'


def test_unknown_first_element_is_not_skipped_and_default_never_supplies_other_fields(tmp_path):
    project,_,ids=build(tmp_path,SOURCE)
    assert invoke(project,ids['Api.buy'],'Buy with product',[{'result':[U,{'__type__':'Product','productName':'X','price':5}]}])=={}
    got=invoke(project,ids['Api.buy'],'Buy with product',[{'result':[{'__type__':'Product','productName':U,'price':5}]}])
    assert 'productName' not in got and got['productPrice'][0]==5
    assert 'cityName' not in got and 'warehouseName' not in got


def test_explicit_negative_choice_never_selects_a_default_item(tmp_path):
    project,_,ids=build(tmp_path,SOURCE)
    history=[{'result':[{'__type__':'Product','productName':'X','price':5}]}]
    assert invoke(project,ids['Api.buy'],'Buy ticket without product',history)=={}
