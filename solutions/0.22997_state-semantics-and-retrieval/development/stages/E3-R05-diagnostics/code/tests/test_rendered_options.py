from analyzer.frontend import Frontend
from analyzer.contracts import ContractGrounder, ContractIndex
from analyzer.html_options import fragment_options
from analyzer.html_rows import analyze_html_rows
from analyzer.state import ScenarioState, U
from builders import build


def fixture(tmp_path,callback=None):
    project,db,ids=build(tmp_path,{'Api.java':'''class Api {
      @GetMapping("/licences") String list(){return "ok";}
      @PostMapping("/licences") int add(@RequestBody Licence input){return input.documentType;}
    } class Licence {int documentType;}
    '''})
    (tmp_path/'page.html').write_text('<table id="records"><tbody></tbody></table><script src="ui.js"></script>')
    callback=callback or '''var rows=response;
      $("#records").find("tbody").html("");
      $("#records").find("tbody").append("<tr><td>"+rows.length+"</td><td><select id='kind'>"+
        "<option value='7'>Student ID</option><option value='9'>Passport</option></select></td></tr>");'''
    (tmp_path/'ui.js').write_text('''function list(){$.ajax({url:"/licences",type:"GET",success:function(response){'''+callback+'''}});}
      function add(){$.ajax({url:"/licences",type:"POST",data:{documentType:$("#kind").val()}});}''')
    frontend=Frontend(project);sites={site['verb']:site for site in frontend.sites.values()}
    state=ScenarioState(db);frontend.enter(sites['GET'],state)
    index=ContractIndex(project,frontend)
    contract=next(c for c in index.contracts.values() if c['entry']==ids['Api.add'])
    return frontend,state,sites,ContractGrounder(project,frontend,index,None,{'facts':{}}),contract


def test_observed_callback_html_preserves_option_value_and_label_provenance(tmp_path):
    frontend,state,sites,grounder,contract=fixture(tmp_path)
    assert len([e for e in sites['GET']['effects'] if e['space']=='options'])==2
    frontend.apply_response(sites['GET'],[{'id':'x'}],state)
    proposal=grounder._bind('Add a licence with Student ID',state,contract,1)
    assert proposal['params']['documentType']==7
    assert 'HTML-fragment' in proposal['bindings']['documentType']['reference']
    assert 'Unknown input: documentType' not in proposal['unresolved']
    fresh=ScenarioState(state.database)
    assert 'documentType' not in grounder._bind('Add licence with Student ID',fresh,contract,1)['params']


def test_unknown_fragment_and_unknown_callback_guard_do_not_create_options(tmp_path):
    callback='''if(response.ok){$("#records").find("tbody").append(response.html+"<select id='kind'><option value='7'>Student ID</option></select>");}'''
    frontend,state,sites,grounder,contract=fixture(tmp_path,callback)
    frontend.apply_response(sites['GET'],{'ok':U,'html':''},state)
    assert state.browser['options']['#records tbody'] is U
    assert 'documentType' not in grounder._bind('Add licence with Student ID',state,contract,1)['params']


def test_fragment_clear_replaces_prior_options_and_loop_sink_is_unsupported(tmp_path):
    callback='''$("#records").find("tbody").html("");for(var i=0;i<response.length;i++){
      $("#records").find("tbody").append("<select id='kind'><option value='7'>Student ID</option></select>");}'''
    frontend,state,sites,_,_=fixture(tmp_path,callback)
    state.browser['options']['#records tbody']=[{'control':'kind','value':'8','label':'Old'}]
    frontend.apply_response(sites['GET'],[],state)
    assert state.browser['options']['#records tbody']==[]


def test_html_fragment_context_template_and_duplicate_ids_do_not_supply_fake_choices():
    assert not fragment_options("<select id='x'><option value='1'>A</option></select><select id='x'><option value='2'>B</option></select>",'div')[0]
    assert not fragment_options("<template><select id='x'><option value='1'>A</option></select></template>",'div')[0]
    assert not fragment_options("<noscript><select id='x'><option value='1'>A</option></select></noscript>",'div')[0]
    options,_=fragment_options("<tr><td><select id='x'><option value='1'>A</option></select></td></tr>",'tbody')
    assert options[0]['control']=='x'


def test_inert_noscript_row_and_repeated_id_cannot_prove_dom_scope():
    out=analyze_html_rows('''<noscript><div v-for="row in items"><button @click="show(row.id)">Show</button></div></noscript>
      <table id="repeated" v-for="item in items"><tbody></tbody></table><div id="once"></div>''')
    assert out['facts']==[]
    assert '#repeated' not in out['containers'] and out['containers']['#once']=='div'
