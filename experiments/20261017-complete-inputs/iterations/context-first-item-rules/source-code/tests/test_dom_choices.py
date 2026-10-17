from analyzer.contracts import ContractGrounder, ContractIndex
from analyzer.frontend import Frontend
from analyzer.state import ScenarioState
from builders import build


def test_dom_created_option_keeps_control_label_and_arbitrary_value(tmp_path):
    project, db, _ = build(tmp_path, {'Api.java': '''class Api {
      @PostMapping("/parcels") int add(@RequestBody Parcel input){return input.giftMode;}
    } class Parcel {int giftMode;}'''})
    (tmp_path/'ui.js').write_text('''function load(){
      var control=document.getElementById("gift_mode");
      var option=document.createElement("option");
      option.value=73; option.innerText="No Gift"; control.appendChild(option);
      var unknown=document.createElement("option");
      unknown.value=runtimeValue(); unknown.innerText="Gift"; control.appendChild(unknown);
    }
    function add(){ $.ajax({url:"/parcels",type:"POST",data:{giftMode:$("#gift_mode").val()}}); }
    ''')
    frontend=Frontend(project)
    options=next(iter(frontend.sites.values()))['options']
    assert [(o['control'],o['label'],o['value']) for o in options] == [('gift_mode','No Gift','73')]
    choices,_=ContractGrounder(project,frontend,ContractIndex(project,frontend),None,{'facts':{}}).step(
        'Add parcel without gift',ScenarioState(db))
    assert choices[0]['params']=={'giftMode':73}


def test_explicit_absence_takes_source_empty_control_branch(tmp_path):
    project, db, _ = build(tmp_path, {'Api.java': '''class Api {
      @PostMapping("/parcels") int add(@RequestBody Parcel input){return input.giftType;}
    } class Parcel {int giftType;String giftLabel;}'''})
    (tmp_path/'ui.js').write_text('''function add(){
      var input={};
      if(null!=$("#summary_giftType").text() && ""!=$("#summary_giftType").text()){
        input.giftType=19;input.giftLabel=$("#gift_label").val();
      } else {input.giftType=73;}
      $.ajax({url:"/parcels",type:"POST",data:JSON.stringify(input)});
    }''')
    frontend=Frontend(project)
    grounder=ContractGrounder(project,frontend,ContractIndex(project,frontend),None,{'facts':{}})
    absent,_=grounder.step('Add parcel without gift',ScenarioState(db))
    assert absent[0]['params']=={'giftType':73,'giftLabel':None}
    unspecified,_=grounder.step('Add parcel',ScenarioState(db))
    assert 'giftType' not in unspecified[0]['params']
    positive,_=grounder.step('Add parcel with gift',ScenarioState(db))
    assert 'giftType' not in positive[0]['params']


def test_confirmation_callback_keeps_enclosing_create_or_update_action(tmp_path):
    project, db, _ = build(tmp_path, {'Api.java': '''class Api {
      @PostMapping("/notebooks") String save(@RequestBody Notebook input){return input.title;}
    } class Notebook {String id;String title;}'''})
    (tmp_path/'ui.js').write_text('''$scope.createNotebook=function(){
      $("#dialog").modal({onConfirm:function(){
        $http({url:"/notebooks",method:"POST",data:{title:$scope.newTitle}});
      }});
    };
    $scope.updateNotebook=function(){
      $("#dialog").modal({onConfirm:function(){
        $http({url:"/notebooks",method:"POST",data:{id:$scope.existingId,title:$scope.editedTitle}});
      }});
    };''')
    frontend=Frontend(project)
    assert {s['action_label'] for s in frontend.sites.values()}=={'createNotebook','updateNotebook'}
    grounder=ContractGrounder(project,frontend,ContractIndex(project,frontend),None,{'facts':{}})
    create,_=grounder.step('Create notebook',ScenarioState(db))
    update,_=grounder.step('Update notebook',ScenarioState(db))
    assert create[0]['site']['action_label']=='createNotebook'
    assert update[0]['site']['action_label']=='updateNotebook'
    assert create[0]['params']['id'] is None
    assert 'id' not in update[0]['params']


def test_option_words_cannot_match_unrelated_clauses_and_choice_persists(tmp_path):
    project, db, _=build(tmp_path,{'Api.java':'''class Api {
      @PostMapping("/shipments") int add(@RequestBody Shipment input){return input.deliveryType;}
    } class Shipment {int deliveryType;}'''})
    (tmp_path/'ui.js').write_text('''function add(){ $.ajax({url:"/shipments",type:"POST",
      data:{deliveryType:unknown()?$("#choice").val():$("#choice").find("option:selected").val()}}); }''')
    (tmp_path/'page.html').write_text('''<script src="ui.js"></script><select id="choice">
      <option value="17">Air Delivery</option><option value="43">Ground Delivery</option></select>''')
    frontend=Frontend(project)
    grounder=ContractGrounder(project,frontend,ContractIndex(project,frontend),None,{'facts':{}})
    choices,_=grounder.step('Book air travel with ground delivery',ScenarioState(db))
    assert choices[0]['params']=={'deliveryType':43}
    repeated,_=grounder.step('Book another shipment',choices[0]['state'])
    assert repeated[0]['params']=={'deliveryType':43}


def test_ordinal_choice_follows_its_ui_producer_not_an_unrelated_listing(tmp_path):
    sources={'Api.java':'''import java.util.*;
      class Api {
        @PostMapping("/parcels") int add(@RequestBody Parcel input){return input.coating;}
        @GetMapping("/coatings") List<CoatingType> list(){List<CoatingType> output=new ArrayList<>();
          for(CoatingType item:CoatingType.values()){output.add(item);} return output;}
      } class Parcel {int coating;}
      enum CoatingType {GOLD(17),SILVER(43);int code;CoatingType(int code){this.code=code;}}
      class Unrelated {List<CoatingType> all(){List<CoatingType> output=new ArrayList<>();
        for(CoatingType item:CoatingType.values()){output.add(item);}return output;}}
    '''}
    def bind(folder, java, transform=''):
        project, db, _=build(folder, {'Api.java':java})
        (folder/'ui.js').write_text('''function load(){ $.ajax({url:"/coatings",type:"GET",
          success:function(reply){var rows=reply;var control=document.getElementById("coat");
          TRANSFORM
          for(var i=0;i<rows.length;i++){var opt=document.createElement("option");
            opt.value=rows[i].code;opt.innerText=rows[i].code;control.appendChild(opt);}}});}
          function add(){ $.ajax({url:"/parcels",type:"POST",data:{coating:$("#coat").val()}}); }
        '''.replace('TRANSFORM',transform))
        frontend=Frontend(project)
        grounder=ContractGrounder(project,frontend,ContractIndex(project,frontend),None,{'facts':{}})
        choices,_=grounder.step('Add parcel with coating of the second type',ScenarioState(db))
        return choices[0]['params']
    assert bind(tmp_path/'plain',sources['Api.java'])['coating']==43
    assert 'coating' not in bind(tmp_path/'filtered',sources['Api.java'].replace(
        'output.add(item);','if(item.code>20){output.add(item);}'))
    assert 'coating' not in bind(tmp_path/'reversed',sources['Api.java'],'rows.reverse();')
