import java.util.*;import org.springframework.stereotype.Component;
import javax.annotation.PostConstruct;
@Component class Cache {Map<String,List<String>> groups=new HashMap<>();
 Set<String> values=new HashSet<>();Set<String> alias;int counter;
 @PostConstruct void init(){groups.put("L",Arrays.asList("A"));groups.put("M",Arrays.asList("B"));
  groups.put("R",Arrays.asList("C"));values.add("A");values.add("B");values.add("C");}
 void apply(String key){counter++;if(counter%2==1){values.removeAll(groups.get(key));}}
 Set<String> read(){return values;}}
class Api {Cache cache;void apply(String key){cache.apply(key);}Set<String> read(){return cache.read();}}