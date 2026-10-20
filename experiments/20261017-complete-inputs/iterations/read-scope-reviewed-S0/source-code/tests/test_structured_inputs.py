from analyzer.contracts import ContractGrounder, ContractIndex, explicit_value
from analyzer.frontend import Frontend
from analyzer.provenance import history_value
from analyzer.scenario_literals import structured_bindings
from analyzer.state import ScenarioState, U
from builders import build


def test_explicit_chain_and_numeric_csv_use_declared_split_fields(tmp_path):
    project, _, ids = build(tmp_path, {'Api.java': '''class Api {
      @PostMapping("/itineraries") String add(@RequestBody ItineraryInput input){return input.locationList;}
    } class ItineraryInput {
      String startLocation;String endLocation;String viaLocation;String locationList;String durationList;
      List<String> getLocations(){return Arrays.asList(locationList.split(","));}
      List<String> getDurations(){return Arrays.asList(durationList.split(","));}
    }'''})
    bindings=structured_bindings(project,ids['Api.add'],
        'Add itinerary North Harbor — Mid Park — West Point with durations 0, 10 and 25')
    assert {key:value[0] for key,value in bindings.items()} == {
        'startLocation':'North Harbor','endLocation':'West Point','viaLocation':'Mid Park',
        'locationList':'North Harbor,Mid Park,West Point','durationList':'0,10,25'}
    assert 'getLocations' in bindings['locationList'][1]
    assert 'getDurations' in bindings['durationList'][1]


def test_csv_shape_is_not_assumed_from_field_name_alone(tmp_path):
    project, _, ids=build(tmp_path,{'Api.java':'''class Api {
      @PostMapping("/itineraries") String add(@RequestBody ItineraryInput input){return input.locationList;}
    } class ItineraryInput {String startLocation;String endLocation;String locationList;String durationList;}'''})
    values=structured_bindings(project,ids['Api.add'],'Add itinerary A → B with durations 0 and 10')
    assert 'locationList' not in values and 'durationList' not in values


def test_field_label_projection_is_unique_and_times_do_not_gain_invented_dates(tmp_path):
    project, _, ids=build(tmp_path,{'Api.java':'''class Api {
      @PostMapping("/runs") String add(@RequestBody Run input){return input.startTime;}
    } class Run {String startTime;String endTime;double basePriceRate;double priorityPriceRate;}'''})
    values=structured_bindings(project,ids['Api.add'],
        'Add run with base rate 0.5, priority rate 1.2, departing 09:00 and arriving 12:00')
    assert {key:item[0] for key,item in values.items()}=={
        'basePriceRate':0.5,'priorityPriceRate':1.2,'startTime':'09:00','endTime':'12:00'}
    assert explicit_value('rate 1 and rate unknown','rate','int')==(U,'')


def test_declared_name_reference_uses_matching_entity_only(tmp_path):
    project, _, ids=build(tmp_path,{'Api.java':'''class Api {
      @PostMapping("/runs") String add(@RequestBody Run input){return input.deviceTypeName;}
    } class Run {String deviceTypeName;}
    class DeviceType {String name;} class ReaderType {String name;}'''})
    history=[{'result':{'__type__':'ReaderType','name':'wrong'}}]
    assert history_value(project,ids['Api.add'],'deviceTypeName','Add run',history) is None
    history.append({'result':{'__type__':'DeviceType','name':'Portable'}})
    assert history_value(project,ids['Api.add'],'deviceTypeName','Add run',history)[1]=='Portable'


def test_structured_literals_are_used_by_grounder_without_ui(tmp_path):
    project, db, _=build(tmp_path,{'Api.java':'''class Api {
      @PostMapping("/experiments") int add(@RequestBody Experiment input){return input.temperatures.size();}
    } class Experiment {List<Integer> temperatures;}'''})
    frontend=Frontend(project)
    choices,_=ContractGrounder(project,frontend,ContractIndex(project,frontend),None,{'facts':{}}).step(
        'Add experiment with temperatures 0, 100 and 250',ScenarioState(db))
    assert choices[0]['params']=={'temperatures':[0,100,250]}


def test_status_and_state_labels_share_source_enum_without_business_codes(tmp_path):
    from analyzer.request_semantics import filter_bindings
    project, _, ids=build(tmp_path,{'Api.java':'''class Api {
      @PostMapping("/parcels/query") int query(@RequestBody ParcelInfo input){return input.state;}
    } class ParcelInfo {boolean enabled;int state;void enableStateQuery(int state){enabled=true;this.state=state;}}
    enum ParcelStatus {CANCEL(37);int code;ParcelStatus(int code){this.code=code;}}'''})
    values=filter_bindings(project,ids['Api.query'],"List parcels filtered by the 'Cancel' status")
    assert {k:v for k,v,_,_ in values}=={'enabled':True,'state':37}


def test_boolean_string_predicate_requires_source_conversion(tmp_path):
    project, _, ids=build(tmp_path,{'Api.java':'''class Api {
      @GetMapping("/quotes/{isInRegion}") boolean quote(@PathVariable String isInRegion){return Boolean.parseBoolean(isInRegion);}
      @GetMapping("/records/{isInRegion}") String lookup(@PathVariable String isInRegion){return isInRegion;}
    }'''})
    assert structured_bindings(project,ids['Api.quote'],'Check quote in the region')['isInRegion'][0]=='true'
    assert structured_bindings(project,ids['Api.quote'],'Check quote not in the region')['isInRegion'][0]=='false'
    assert 'isInRegion' not in structured_bindings(project,ids['Api.quote'],'Check quote')
    assert 'isInRegion' not in structured_bindings(project,ids['Api.lookup'],'Read record in the region')
