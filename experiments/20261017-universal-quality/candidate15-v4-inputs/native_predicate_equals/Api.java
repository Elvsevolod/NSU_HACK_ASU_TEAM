class Api {@Autowired Store store;String entry(){
        if(store.visible(1).isEmpty()){return none();}return found();}
        String found(){return "found";}String none(){return "none";}}
        @Entity @Table(name="parts") class Part {@Id String id;int quantity;}
        interface Store extends JpaRepository<Part,String>{
          @Query(value="SELECT * FROM parts WHERE quantity = ?1",nativeQuery=true)
          List<Part> visible(int threshold);}