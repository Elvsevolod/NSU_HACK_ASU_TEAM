import java.util.*;import jakarta.persistence.*;import org.springframework.data.jpa.repository.JpaRepository;
      @Entity @Table(name="markers")class Marker{@Id String id;String text;}
      interface Store extends JpaRepository<Marker,String>{Optional<Marker> findById(String id);}
      class Api{Store store;Object entry(boolean finish,List<String> visits){
        Marker m=store.findById("anchor").orElseThrow();
        Set<String> keys=new HashSet<>(Arrays.asList("A","B","C"));Map<String,String> values=new HashMap<>();
        for(String key:keys){values.put(key,mark(key,visits));}
        if(finish)return read(values);throw new IllegalStateException();}
        String read(Map<String,String> values){return values.get("B");}
        String mark(String key,List<String> visits){ return key;}}