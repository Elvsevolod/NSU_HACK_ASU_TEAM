from analyzer.engine import Engine
from analyzer.state import ScenarioState,U
from builders import build


def test_integral_python_values_do_not_change_a_declared_double_division(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'class Api {double entry(){double x=2;return x/4;}}'})
    assert Engine(project,ScenarioState(db)).run(ids['Api.entry'],{})==0.5


def test_standard_double_parser_preserves_its_source_return_type(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'class Api {double entry(){return Double.parseDouble("0.5")+Double.parseDouble("0.25");}}'})
    assert Engine(project,ScenarioState(db)).run(ids['Api.entry'],{})==0.75


def test_declared_double_database_field_keeps_floating_point_arithmetic(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''@Entity @Table(name="rates") class Rate {
      @Id int id;double factor;double getFactor(){return factor;}}
      interface Store extends JpaRepository<Rate,Integer>{Rate findById(int id);}
      class Api {@Autowired Store store;double entry(){Rate r=store.findById(1);return 3*r.getFactor();}}'''
      },rows={'rates':[{'id':1,'factor':2}]})
    result=Engine(project,ScenarioState(db)).run(ids['Api.entry'],{})
    assert type(result) is float and result==6.0


def test_unsupported_float_rounding_is_diagnosed_instead_of_using_double_semantics(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'class Api {float entry(){float x=16777216;return x+1;}}'})
    engine=Engine(project,ScenarioState(db));assert engine.run(ids['Api.entry'],{}) is U
    assert engine.approximate and any('float' in warning for warning in engine.warnings)
