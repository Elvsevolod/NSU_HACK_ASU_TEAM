"""C02 source expectations; allocation must not execute a thread/task callback."""
import pytest
from analyzer.paths import run_paths
from analyzer.state import ScenarioState, U
from builders import build


def run(tmp_path, source, params=None):
    p,db,ids=build(tmp_path,{'Api.java':source})
    return run_paths(p,ScenarioState(db),ids['Api.entry'],params or {},limit=4),ids


@pytest.mark.parametrize('expression',[
    'Executors.newFixedThreadPool(2)',
    'Executors.newFixedThreadPool(2,new CustomizableThreadFactory("workers-"))',
    'java.util.concurrent.Executors.newFixedThreadPool(2,new CustomizableThreadFactory())',
])
def test_unused_pool_allocation_preserves_the_source_suffix(tmp_path,expression):
    rows,ids=run(tmp_path,'''import java.util.concurrent.*;
      import org.springframework.scheduling.concurrent.CustomizableThreadFactory;
      class Api{static final ExecutorService pool=EXPR;
        int entry(){return after();}int after(){return 19;}}'''.replace('EXPR',expression))
    assert rows and all(r['result']==19 and r['engine'].outcome=='returned' for r in rows)
    assert all(('','executes',ids['Api.after']) in r['engine'].edges for r in rows)
    assert not any(e.get('operation') in ('newFixedThreadPool','<init>') and e.get('unscoped')
                   for r in rows for e in r['engine'].effect_events)


def test_allocation_keeps_argument_constructor_effect_but_never_calls_factory(tmp_path):
    rows,ids=run(tmp_path,'''import java.util.concurrent.*;
      class Factory implements ThreadFactory{
        Factory(){Api.count++;}public Thread newThread(Runnable task){Api.count+=100;throw new IllegalStateException();}}
      class Api{static int count=0;int entry(){ExecutorService pool=Executors.newFixedThreadPool(2,new Factory());return count;}}''')
    assert rows and all(r['result']==1 and r['engine'].outcome=='returned' for r in rows)
    assert all(('','executes',ids['Factory.<init>']) in r['engine'].edges for r in rows)
    assert not any(('','executes',ids['Factory.newThread']) in r['engine'].edges for r in rows)


@pytest.mark.parametrize('expression,exception',[
    ('Executors.newFixedThreadPool(0)','IllegalArgumentException'),
    ('Executors.newFixedThreadPool(-2,null)','IllegalArgumentException'),
    ('Executors.newFixedThreadPool(2,null)','NullPointerException'),
])
def test_invalid_pool_keeps_java_throw_and_does_not_execute_suffix(tmp_path,expression,exception):
    rows,ids=run(tmp_path,'''import java.util.concurrent.*;class Api{
      int entry(){try{EXPR;return after();}catch(EXCEPTION ex){return 7;}}int after(){return 99;}}'''
      .replace('EXPR',expression).replace('EXCEPTION',exception))
    assert rows and all(r['result']==7 and r['engine'].outcome=='returned' for r in rows)
    assert not any(('','executes',ids['Api.after']) in r['engine'].edges for r in rows)


def test_unknown_pool_size_is_not_assumed_positive(tmp_path):
    rows,ids=run(tmp_path,'''import java.util.concurrent.*;class Api{
      int entry(int count){Executors.newFixedThreadPool(count);return after();}int after(){return 99;}}''',{'count':U})
    assert rows and all(r['engine'].outcome=='unsupported_semantics boundary' for r in rows)
    assert not any(('','executes',ids['Api.after']) in r['engine'].edges for r in rows)


def test_submission_is_an_explicit_boundary_not_a_completed_task(tmp_path):
    rows,ids=run(tmp_path,'''import java.util.concurrent.*;class Api{
      int entry(){ExecutorService pool=Executors.newFixedThreadPool(1);pool.submit(()->task());return after();}
      int task(){return 51;}int after(){return 99;}}''')
    assert rows and all(r['engine'].outcome=='unsupported_semantics boundary' for r in rows)
    assert not any(('','executes',ids['Api.task']) in r['engine'].edges or ('','executes',ids['Api.after']) in r['engine'].edges for r in rows)


def test_source_namesake_factory_keeps_its_source_calls(tmp_path):
    rows,ids=run(tmp_path,'''import java.util.concurrent.*;
      class Executors{static int newFixedThreadPool(int n){return 37;}}
      class Api{int entry(){return Executors.newFixedThreadPool(2);}}''')
    assert rows and all(r['result']==37 for r in rows)
    assert all(('','executes',ids['Executors.newFixedThreadPool']) in r['engine'].edges for r in rows)
