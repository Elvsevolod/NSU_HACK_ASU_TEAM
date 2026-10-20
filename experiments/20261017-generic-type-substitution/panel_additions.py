"""Additional source-fixed references for inherited JSON type mechanisms."""
suffix='String accepted(){return "ok";}String rejected(){return "bad";}'
cases.append({'name':'inherited_map_http','family':'inherited_generic_http','entry':'Client.entry','remote_units':True,'sources':{
 'Client.java':'''import org.springframework.web.client.RestTemplate;class Client{RestTemplate rest;String entry(){
 Response response=rest.getForObject("http://stock/data",Response.class);
 if("ready".equals(response.payload.get("mode"))){return accepted();}return rejected();}'''+suffix+'}',
 'Stock.java':'''import java.util.*;class Wire{public Map payload;}class Base<T>{public T payload;}
 class Response extends Base<Map<String,String>>{}class Api{@GetMapping("/data") Wire data(){
 Wire result=new Wire();Map map=new HashMap();map.put("mode","ready");result.payload=map;return result;}}'''},
 'methods':['Api.data','Client.accepted'],'calls':[('Client.entry','Client.accepted')],
 'remote':[('Client.entry','Api.data')]})

cases.append({'name':'nested_inherited_value_drives_table','family':'nested_generic_data_selection','entry':'Client.entry','remote_units':True,'sources':{
 'Client.java':'''import org.springframework.web.client.RestTemplate;import org.springframework.core.ParameterizedTypeReference;
 import org.springframework.http.HttpMethod;class Client{RestTemplate rest;Store stock;AuditStore audit;String entry(){
 Response<Item> response=rest.exchange("http://stock/data",HttpMethod.GET,null,
 new ParameterizedTypeReference<Response<Item>>(){}).getBody();
 if("ready".equals(response.payload.get("items").get(0).code)){stock.findAll();return accepted();}
 audit.findAll();return rejected();}'''+suffix+'}',
 'Stock.java':'''import java.util.*;class Item{public String code="ready";}class Wire{public Map payload;}
 class Base<T>{public T payload;}class Middle<T> extends Base<Map<String,List<T>>>{}class Response<T> extends Middle<T>{}
 class Api{@GetMapping("/data") Wire data(){Wire result=new Wire();Map map=new HashMap();
 map.put("items",Arrays.asList(new Item()));result.payload=map;return result;}}
 @Entity @Table(name="items") class Part{@Id String id;}@Entity @Table(name="events") class Event{@Id String id;}
 interface Store extends JpaRepository<Part,String>{List<Part> findAll();}
 interface AuditStore extends JpaRepository<Event,String>{List<Event> findAll();}'''},
 'rows':{'items':[],'events':[]},'methods':['Api.data','Client.accepted'],'calls':[('Client.entry','Client.accepted')],
 'remote':[('Client.entry','Api.data')],'data':[('Client.entry','items')]})

for name,base in [('raw_upper_bound','class Base<T extends Item>{public T payload;}'),
                  ('raw_parameter_named_string','class Base<String extends Item>{public String payload;}'),
                  ('raw_dependent_bound','class Base<T extends Item,U extends T>{public U payload;}')]:
    cases.append({'name':name,'family':name,'entry':'Api.entry','sources':{
     'Api.java':'''import com.fasterxml.jackson.databind.ObjectMapper;class Item{public String code="ready";}
     class Wire{public Object payload;}'''+base+'''class Response extends Base{}class Api{String entry(){
     Wire wire=new Wire();wire.payload=new Item();Response response=new ObjectMapper().convertValue(wire,Response.class);
     if("ready".equals(response.payload.code)){return accepted();}return rejected();}'''+suffix+'}'},
     'methods':['Api.accepted'],'calls':[('Api.entry','Api.accepted')]})

cases.append({'name':'all_interface_parents','family':'source_interface_parents','entry':'Api.entry','sources':{
 'Api.java':'''interface First{}interface Second{String read();}interface Both extends First,Second{}
 class Worker implements Both{public String read(){return "ready";}}class Api{String entry(){
 Both worker=new Worker();return worker.read();}}'''},
 'methods':['Worker.read'],'calls':[('Api.entry','Worker.read')]})

cases.append({'name':'explicit_ignore_unknown','family':'json_unknown_property_policy','entry':'Api.entry','sources':{
 'Api.java':'''import com.fasterxml.jackson.databind.ObjectMapper;import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
 @JsonIgnoreProperties(ignoreUnknown=true) class Item{public String code;}class Wire{public String code="ready";public String extra="ignored";}
 class Api{String entry(){Item item=new ObjectMapper().convertValue(new Wire(),Item.class);
 if("ready".equals(item.code)){return accepted();}return rejected();}'''+suffix+'}'},
 'methods':['Api.accepted'],'calls':[('Api.entry','Api.accepted')]})
