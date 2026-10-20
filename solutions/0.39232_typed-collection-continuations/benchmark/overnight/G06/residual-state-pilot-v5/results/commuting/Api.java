import java.util.*;import org.springframework.stereotype.Component;
import javax.annotation.PostConstruct;
import org.springframework.beans.factory.annotation.Autowired;
@Component class Cache {Map<String,List<String>> groups=new HashMap<>();
 Set<String> values=new HashSet<>();Set<String> alias;int counter;
 @PostConstruct void init(){groups.put("L",Arrays.asList("A"));groups.put("M",Arrays.asList("B"));
  groups.put("R",Arrays.asList("C"));values.add("A");values.add("B");values.add("C");}
 void apply(String key){values.removeAll(groups.get(key));}
 Set<String> read(){return values;}}
@Component class Api {@Autowired Cache cache;void apply(String key){cache.apply(key);}Set<String> read(){return cache.read();}}