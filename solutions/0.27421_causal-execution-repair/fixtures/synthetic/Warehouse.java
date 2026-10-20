import java.util.*;class Warehouse {Store store;
      @PostMapping("/reservations") Booking reserve(@RequestBody BookingInput input){
        if(!input.enabled){throw new IllegalArgumentException();}
        Booking item=new Booking();item.id=input.id;item.title=input.title;store.save(item);return item;}
      @GetMapping("/reservations") List<Booking> list(){return store.findAll();}
      @GetMapping("/reservations/{id}") Booking read(@PathVariable String id){return store.findById(id);}
      @DeleteMapping("/reservations/{id}") void remove(@PathVariable String id){store.deleteById(id);}}
      class BookingInput {public String id;public String title;public boolean enabled;}
      @Entity @Table(name="bookings") class Booking {@Id public String id;public String title;}
      interface Store extends JpaRepository<Booking,String>{Booking save(Booking input);Booking findById(String id);List<Booking> findAll();void deleteById(String id);}