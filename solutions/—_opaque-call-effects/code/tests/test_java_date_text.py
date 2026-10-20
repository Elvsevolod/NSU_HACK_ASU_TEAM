from datetime import datetime
from analyzer.engine import Engine
from analyzer.paths import run_paths
from analyzer.state import ScenarioState, U
from builders import build


def test_java_date_text_is_not_an_iso_string_and_numeric_parser_throws(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''class Api {long entry(){
      Date date=new Date(0);String text=date.toString();
      if(text.length()<=10){wrong();}
      try {return new SimpleDateFormat("yyyy-MM-dd HH:mm:ss").parse(text).getTime();}
      catch(ParseException e){return 7;}}
      void wrong(){}}'''})
    outcomes=run_paths(project,ScenarioState(db),ids['Api.entry'],{})
    assert len(outcomes)==1 and outcomes[0]['result']==7
    assert ids['Api.wrong'] not in {t for _,r,t in outcomes[0]['engine'].edges if r=='calls'}


def test_invalid_numeric_date_prefix_throws_but_lenient_cases_stay_unknown(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''class Api {long entry(String input){
      try {return new SimpleDateFormat("dd/MM/yyyy").parse(input).getTime();}
      catch(ParseException ex){return 7;}}}'''})
    engine=Engine(project,ScenarioState(db))
    assert engine.run(ids['Api.entry'],{'input':'not a date'})==7
    engine=Engine(project,ScenarioState(db),conservative=True)
    assert engine.run(ids['Api.entry'],{'input':'32/01/2026'}) is U
    assert engine.approximate and engine.warnings


def test_clock_and_hour_of_day_arithmetic_use_the_supplied_instant(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''class Api {long entry(){
      Calendar c=Calendar.getInstance();c.setTime(new Date(System.currentTimeMillis()));
      c.add(Calendar.HOUR_OF_DAY,-1);return c.getTime().getTime();}}'''})
    state=ScenarioState(db);state.now=datetime(1970,1,2)
    assert Engine(project,state).run(ids['Api.entry'],{})==82800000


def test_date_url_does_not_silently_choose_an_iso_parser_success(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''import org.springframework.web.client.RestTemplate;import org.springframework.web.client.RestOperations;class Caller {RestTemplate rest;long entry(){
      return rest.getForObject("http://service/dates/"+new Date(0),Long.class);}}
      class Api {@GetMapping("/dates/{date}") long get(@PathVariable String date){
        try {new SimpleDateFormat("yyyy-MM-dd").parse(date);return 1;}
        catch(ParseException ex){return 2;}}}'''})
    outcomes=run_paths(project,ScenarioState(db),ids['Caller.entry'],{})
    assert {o['result'] for o in outcomes}=={2}
    assert all(o['engine'].approximate and any('time zone' in w for w in o['engine'].warnings) for o in outcomes)
