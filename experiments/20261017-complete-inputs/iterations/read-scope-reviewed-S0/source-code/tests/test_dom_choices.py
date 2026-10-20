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
