from analyzer.engine import Engine
from analyzer.state import ScenarioState,U
from builders import build


def test_joined_singleton_receiver_and_cache_share_later_writes(tmp_path):
    p,db,ids=build(tmp_path,{'Api.java':'''import org.springframework.stereotype.Component;
      import javax.annotation.PostConstruct;
      @Component class Counter {int revision;@PostConstruct void init(){revision=7;}
        int set(boolean flag){if(flag){revision=8;}else{revision=9;}revision=10;return revision;}
        int read(){return revision;}}
      class Api {Counter counter;int write(boolean flag){return counter.set(flag);}int read(){return counter.read();}}'''})
    first=Engine(p,ScenarioState(db),conservative=True)
    assert first.run(ids['Api.write'],{'flag':U})==10
    second=Engine(p,first.state)
    assert second.run(ids['Api.read'],{})==10
