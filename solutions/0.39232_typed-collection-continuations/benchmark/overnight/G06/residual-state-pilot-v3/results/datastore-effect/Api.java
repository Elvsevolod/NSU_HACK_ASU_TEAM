import java.util.*;import org.springframework.stereotype.Component;
import javax.annotation.PostConstruct;import org.springframework.data.jpa.repository.JpaRepository;import jakarta.persistence.*;@Entity @Table(name="control") class Revision{@Id public String id;public int revision;}interface Controls extends JpaRepository<Revision,String>{Optional<Revision> findById(String id);Revision save(Revision row);}
import org.springframework.beans.factory.annotation.Autowired;
@Component class Cache {@Autowired Controls controls;Map<String,List<String>> groups=new HashMap<>();
 Set<String> values=new HashSet<>();Set<String> alias;int counter;
 @PostConstruct void init(){groups.put("L",Arrays.asList("A"));groups.put("M",Arrays.asList("B"));
  groups.put("R",Arrays.asList("C"));values.add("A");values.add("B");values.add("C");}
 void apply(String key){Revision row=controls.findById("one").get();row.revision++;controls.save(row);values.removeAll(groups.get(key));}
 Set<String> read(){return values;}}
@Component class Api {@Autowired Cache cache;void apply(String key){cache.apply(key);}Set<String> read(){return cache.read();}}