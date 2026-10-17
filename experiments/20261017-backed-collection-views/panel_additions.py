"""Manual references for additional generic mechanisms; added before prediction."""
suffix='String accepted(){return "ok";}String rejected(){return "bad";}'
for name,statements,test in [
 ('backed_view_size','Map map=new HashMap();Collection view=map.values();map.put("k","v");','view.size()==1'),
 ('view_clear','Map map=new HashMap();map.put("k","v");map.keySet().clear();','map.isEmpty()'),
 ('entry_write','Map map=new HashMap();map.put("k","old");Map.Entry entry=(Map.Entry)map.entrySet().iterator().next();entry.setValue("new");','"new".equals(map.get("k"))'),
 ('boxed_value_equality','Map map=new HashMap();map.put("k",1L);','!map.values().contains(1)'),
 ('linked_key_order','Map map=new LinkedHashMap();map.put("first",1);map.put("last",2);','"first".equals(map.keySet().iterator().next())'),
]:
    cases.append({'name':name,'family':name,'entry':'Api.entry','sources':{'Api.java':
      'import java.util.*;class Api{String entry(){'+statements+'if('+test+'){return accepted();}return rejected();}'+suffix+'}'},
      'methods':['Api.accepted'],'calls':[('Api.entry','Api.accepted')]})

cases.append({'name':'iterator_remove_twice','family':'iterator_failure','entry':'Api.entry','sources':{
 'Api.java':'import java.util.*;class Api{String entry(){Map map=new HashMap();map.put("k","v");Iterator it=map.keySet().iterator();'
 'try{it.next();it.remove();it.remove();return rejected();}catch(IllegalStateException error){return accepted();}}'+suffix+'}'},
 'methods':['Api.accepted'],'calls':[('Api.entry','Api.accepted')]})

cases.append({'name':'caller_heap_join','family':'heap_alias_join','entry':'Api.entry','conservative_engine':True,'sources':{
 'Api.java':'import java.util.*;class Api{String entry(boolean flag){Map map=new HashMap();update(map,flag);'
 'if("ready".equals(map.get("key"))){return accepted();}return rejected();}void update(Map input,boolean flag){'
 'if(flag){input.put("key","ready");}else{input.put("key","ready");}}'+suffix+'}'},
 'methods':['Api.update','Api.accepted'],'calls':[('Api.entry','Api.update'),('Api.entry','Api.accepted')]})

cases.append({'name':'view_driven_remote','family':'view_remote_selection','entry':'Client.entry','remote_units':True,'sources':{
 'Client.java':'''import java.util.*;import org.springframework.web.client.RestTemplate;
 class Client{RestTemplate rest;String entry(){Map map=new HashMap();Set keys=map.keySet();map.put("ready",true);
 if(keys.contains("ready")){return rest.getForObject("http://stock/ready",String.class);}
 return rest.getForObject("http://stock/wrong",String.class);}}''',
 'Stock.java':'''class Api{@GetMapping("/ready") String ready(){return "ok";}
 @GetMapping("/wrong") String wrong(){return "bad";}}'''},
 'methods':['Api.ready'],'remote':[('Client.entry','Api.ready')]})

cases.append({'name':'large_copy_driven_data','family':'commuting_map_copy','entry':'Api.entry','sources':{
 'Api.java':'import java.util.*;class Api{Store stock;AuditStore audit;String entry(){Map<String,String> source=new HashMap();'+
 ''.join('source.put("k'+str(i)+'","v'+str(i)+'");' for i in range(80))+
 'Map target=new HashMap();for(String key:source.keySet()){target.put(key,source.get(key));}'
 'if(target.size()==80){stock.findAll();return accepted();}audit.findAll();return rejected();}'+suffix+'}'
 '@Entity @Table(name="items") class Item{@Id String id;}@Entity @Table(name="events") class Event{@Id String id;}'
 'interface Store extends JpaRepository<Item,String>{List<Item> findAll();}'
 'interface AuditStore extends JpaRepository<Event,String>{List<Event> findAll();}'},
 'rows':{'items':[],'events':[]},'methods':['Api.accepted'],'calls':[('Api.entry','Api.accepted')],'data':[('Api.entry','items')]})

# Union reference: either first key is allowed by the HashMap API. No specific
# JVM hashing implementation or Python insertion order forms the oracle.
cases.append({'name':'unordered_view_selection','family':'unordered_map_bound','entry':'Api.entry','sources':{
 'Api.java':'import java.util.*;class Api{String entry(){Map map=new HashMap();map.put("left",1);map.put("right",2);'
 'if("left".equals(map.keySet().iterator().next())){return accepted();}return rejected();}'+suffix+'}'},
 'methods':['Api.accepted','Api.rejected'],'calls':[('Api.entry','Api.accepted'),('Api.entry','Api.rejected')]})

# A measured limit: Map-view stream callbacks remain unsupported, and are not
# described as implemented just because other collection probes pass.
cases.append({'name':'view_stream_limit','family':'view_stream_boundary','entry':'Api.entry','sources':{
 'Api.java':'import java.util.*;import java.util.stream.Collectors;class Api{Object entry(){Map<String,String> map=new HashMap();'
 'map.put("key","value");return map.values().stream().map(value->accepted()).collect(Collectors.toList());}'+suffix+'}'},
 'methods':['Api.accepted'],'calls':[('Api.entry','Api.accepted')]})
