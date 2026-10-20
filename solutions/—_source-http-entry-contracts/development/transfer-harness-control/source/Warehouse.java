import java.util.*;import org.springframework.data.jpa.repository.JpaRepository;
        class Warehouse{Store store;
        @GetMapping("/equipment/{id}")String read(@PathVariable String id){return store.findById(id).get().status;}
        @PostMapping("/reserve/{id}")String reserve(@PathVariable String id){Item item=store.findById(id).get();
          item.status="reserved";store.save(item);return item.status;}}
        @Entity @Table(name="equipment")class Item{@Id String id;public String status;}
        interface Store extends JpaRepository<Item,String>{Optional<Item> findById(String id);Item save(Item value);}