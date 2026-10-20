from datetime import datetime
from analyzer.engine import Engine
from analyzer.state import ScenarioState
from builders import build


def test_source_postconstruct_initializes_private_key_without_startup_edges(tmp_path):
    source='''import java.util.*;import io.jsonwebtoken.*;import javax.annotation.PostConstruct;
      import org.springframework.stereotype.Component;
      @Component class Signer {private String secret="secret";private long duration=60000;
       @PostConstruct void init(){secret=Base64.getEncoder().encodeToString(secret.getBytes());}
       String token(){return Jwts.builder().setSubject("reader").setExpiration(new Date(new Date().getTime()+duration))
        .signWith(SignatureAlgorithm.HS256,secret).compact();}}
      class Api{Signer signer;String entry(){return signer.token();}}'''
    (tmp_path/'pom.xml').write_text('<project><dependencies><dependency><groupId>io.jsonwebtoken</groupId>'
      '<artifactId>jjwt</artifactId><version>0.8.0</version></dependency></dependencies></project>')
    project,db,ids=build(tmp_path,{'Api.java':source})
    engine=Engine(project,ScenarioState(db,{'clock':datetime(2026,10,18)}))
    result=engine.run(ids['Api.entry'],{})
    assert isinstance(result,str) and len(result.split('.'))==3
    assert ids['Signer.init'] not in {t for _,k,t in engine.edges if k=='executes'}
    assert ids['Signer.token'] in {t for _,k,t in engine.edges if k=='executes'}
    assert not engine.approximate
