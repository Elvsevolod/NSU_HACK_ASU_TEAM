from analyzer.__main__ import analyze
from analyzer.contracts import ContractGrounder, ContractIndex, read_static_context
from analyzer.frontend import Frontend
from analyzer.paths import join_states
from analyzer.state import ScenarioState
from builders import build
import pytest


@pytest.mark.parametrize('missing_request',[False,True])
def test_unobserved_preparation_does_not_become_confirmed_in_next_request(tmp_path,missing_request):
    project,db,ids=build(tmp_path,{'Api.java':'''import java.util.*;
      class Api {
        @Autowired WidgetRepository widgets;
        @PostMapping("/widgets") Widget create(@RequestBody Input input){
          Widget widget=new Widget();widget.id="known";widget.enabled=input.enabled;
          widgets.save(widget);return widget;
        }
        @GetMapping("/widgets/known") String inspect(){
          Widget widget=widgets.findById("known").get();
          if(widget.enabled){return approved();}return rejected();
        }
        String approved(){return "approved";}String rejected(){return "rejected";}
      }
      class Input {boolean enabled;}
      @Entity @Table(name="widgets") class Widget {@Id String id;boolean enabled;}
      interface WidgetRepository extends JpaRepository<Widget,String>{}
    '''},rows={'widgets':[]})
    (tmp_path/'page.html').write_text('<span id="enabled"></span><script src="ui.js"></script>')
    (tmp_path/'ui.js').write_text('''function createWidget(){$('#enabled').text('true');
      $.ajax({url:'/widgets',type:'POST',data:{enabled:$('#enabled').text()}});}
      function inspectWidget(){$.ajax({url:'/widgets/known',type:'GET'});}''')
    frontend=Frontend(project)
    class IncompleteGrounder(ContractGrounder):
        def step(self, action, state, scenario_text='', prepared_proposal=None):
            if action == 'Create widget':
                return [],{'candidates':[],'proposal':{'hypotheses':[]},
                           'unresolved':['Unsupported source mutation']}
            return super().step(action,state,scenario_text,prepared_proposal)
    if missing_request:
        db.tables[('service','widgets')]=[{'id':'known','enabled':True}]
    context=read_static_context({'clock':'System clock is 2 November 2031'})
    _,report=analyze(project,frontend,ContractIndex(project,frontend),None,db,context,
        {'id':'widgets','steps':[{'n':1,'action':'Create widget'},{'n':2,'action':'Inspect widget'}]},
        grounder_type=IncompleteGrounder if missing_request else ContractGrounder)
    if missing_request:
        assert report['steps'][0]['alternatives']==[]
    else:
        assert any('DOM preparation' in issue for issue in report['steps'][0]['alternatives'][0]['unresolved'])
    second=report['steps'][1]['alternatives'][0]
    assert ids['Api.approved'] in {e['target'] for e in second['edges'] if e['relation']=='executes'}
    assert ids['Api.approved'] not in {e['target'] for e in report['confirmed']}
    assert any('earlier analysis assumptions' in issue for issue in second['unresolved'])


def test_join_keeps_assumptions_from_every_alternative(tmp_path):
    _,db,_=build(tmp_path,{'Api.java':'class Api {String read(){return "ok";}}'})
    left,right=ScenarioState(db),ScenarioState(db)
    right.analysis_assumptions=['unobserved source callback']
    right.limitations=['alternative-specific unsupported mutation']
    merged=join_states([left,right])
    assert 'unobserved source callback' in merged.analysis_assumptions
    assert 'alternative-specific unsupported mutation' in merged.limitations
