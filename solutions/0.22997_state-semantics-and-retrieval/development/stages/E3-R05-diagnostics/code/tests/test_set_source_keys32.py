"""R04 expected source contracts, written before the Set implementation."""
import pytest
from analyzer.engine import Engine
from analyzer.state import ScenarioState,U
from builders import build


def model(tmp_path,body,key=''):
    return build(tmp_path,{'Api.java':'import java.util.*;'+key+'''class Api{Object entry(){'''+body+'''}int after(){return 99;}}'''})


KEY='''class WarehouseKey{int aisle;String bin;WarehouseKey(int a,String b){aisle=a;bin=b;}
  public int hashCode(){return 7;}
  public boolean equals(Object other){if(!(other instanceof WarehouseKey))return false;
    WarehouseKey key=(WarehouseKey)other;return aisle==key.aisle && bin.equals(key.bin);}}'''


def test_equal_keys_and_hash_collision(tmp_path):
    p,db,ids=model(tmp_path,'''Set<WarehouseKey> keys=new HashSet<>();
      boolean a=keys.add(new WarehouseKey(1,"A"));boolean b=keys.add(new WarehouseKey(1,"A"));
      boolean c=keys.add(new WarehouseKey(2,"B"));return Arrays.asList(a,b,c,keys.size());''',KEY)
    e=Engine(p,ScenarioState(db));assert e.run(ids['Api.entry'],{})==[True,False,True,2]
    assert ('','executes',ids['WarehouseKey.hashCode']) in e.edges
    assert ('','executes',ids['WarehouseKey.equals']) in e.edges
    assert not e.approximate


def test_hash_runs_on_first_add_identity_shortcut_skips_equals(tmp_path):
    key='''class Key{int hashes;int comparisons;public int hashCode(){hashes++;return 1;}
      public boolean equals(Object other){comparisons++;return true;}}'''
    p,db,ids=model(tmp_path,'''Key key=new Key();Set<Key> keys=new HashSet<>();
      keys.add(key);keys.add(key);keys.add(new Key());keys.add(null);keys.add(null);
      return Arrays.asList(key.hashes,key.comparisons,keys.size());''',key)
    e=Engine(p,ScenarioState(db));assert e.run(ids['Api.entry'],{})==[2,0,2]


def test_hash_throw_keeps_alias_effect_before_catch(tmp_path):
    key='''class Counter{int value;}class Key{Counter counter;Key(Counter c){counter=c;}
      public int hashCode(){counter.value++;throw new IllegalStateException();}}
    '''
    p,db,ids=model(tmp_path,'''Counter c=new Counter();Key key=new Key(c);Set<Key> keys=new HashSet<>();
      try{keys.add(key);return after();}catch(IllegalStateException ex){return Arrays.asList(c.value,keys.size());}''',key)
    e=Engine(p,ScenarioState(db));assert e.run(ids['Api.entry'],{})==[1,0]
    assert ('','executes',ids['Api.after']) not in e.edges


def test_mutation_does_not_rehash_stored_key(tmp_path):
    key='class Key{int code;public int hashCode(){return code;}public boolean equals(Object other){return this==other;}}'
    p,db,ids=model(tmp_path,'''Key key=new Key();key.code=1;Set<Key> keys=new HashSet<>();keys.add(key);
      key.code=2;return Arrays.asList(keys.contains(key),keys.size());''',key)
    e=Engine(p,ScenarioState(db));assert e.run(ids['Api.entry'],{})==[False,1]


def test_equals_throw_preserves_incoming_alias_write_and_existing_element(tmp_path):
    key='''class Counter{int count;}class Key{Counter counter;Key(Counter c){counter=c;}
      public int hashCode(){return 1;}public boolean equals(Object other){counter.count++;throw new IllegalStateException();}}'''
    p,db,ids=model(tmp_path,'''Counter first=new Counter();Counter second=new Counter();Set<Key> keys=new HashSet<>();
      keys.add(new Key(first));try{keys.add(new Key(second));return after();}
      catch(IllegalStateException ex){return Arrays.asList(first.count,second.count,keys.size());}''',key)
    e=Engine(p,ScenarioState(db));assert e.run(ids['Api.entry'],{})==[0,1,1]
    assert ('','executes',ids['Api.after']) not in e.edges


def test_different_hash_skips_equals_and_null_has_no_callback(tmp_path):
    key='''class Key{int code;int checks;Key(int x){code=x;}public int hashCode(){return code;}
      public boolean equals(Object other){checks++;return true;}}'''
    p,db,ids=model(tmp_path,'''Key a=new Key(1);Key b=new Key(2);Set<Key> keys=new HashSet<>();
      keys.add(null);keys.add(a);keys.add(b);return Arrays.asList(a.checks,b.checks,keys.size());''',key)
    e=Engine(p,ScenarioState(db));assert e.run(ids['Api.entry'],{})==[0,0,3]


def test_default_lombok_leaf_membership(tmp_path):
    key='import lombok.Data;@Data class WarehouseKey{int aisle;String bin;WarehouseKey(int a,String b){aisle=a;bin=b;}}'
    p,db,ids=model(tmp_path,'Set<WarehouseKey> keys=new HashSet<>();keys.add(new WarehouseKey(1,"A"));keys.add(new WarehouseKey(1,"A"));return keys.size();',key)
    e=Engine(p,ScenarioState(db));assert e.run(ids['Api.entry'],{})==1 and not e.approximate
    assert all(not part.startswith('generated:') for edge in e.edges for part in edge)


@pytest.mark.parametrize('key',[
 'class Data{} @Data class Key{int aisle;}',
 'import lombok.Data;class Base{int hidden;}@Data class Key extends Base{int aisle;}',
 'import lombok.EqualsAndHashCode;@EqualsAndHashCode(exclude="aisle")class Key{int aisle;}',
 'import lombok.Data;@Data class Key{int[] aisles;}',
 'import lombok.Data;@Data class Key{int aisle;int getAisle(){return 9;}}'])
def test_generated_outside_scope_stops_before_normal_sentinel(tmp_path,key):
    p,db,ids=model(tmp_path,'Set<Key> keys=new HashSet<>();keys.add(new Key());return after();',key)
    e=Engine(p,ScenarioState(db));assert e.run(ids['Api.entry'],{}) is U
    assert e.outcome=='unsupported_semantics boundary'
    assert ('','executes',ids['Api.after']) not in e.edges
