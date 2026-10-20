class Api {Store store;AuditStore audits;String entry(){
   if(store.above(1).isEmpty()){audits.findAll();return none();}return ready();}
   String none(){return "none";}String ready(){return "ready";}}
   @Entity @Table(name="parts") class Part {@Id String id;int quantity;}
   @Entity @Table(name="audits") class Audit {@Id String id;}
   interface Store extends JpaRepository<Part,String>{
    @Query(value="SELECT * FROM parts WHERE quantity > ?1",nativeQuery=true) List<Part> above(int threshold);}
   interface AuditStore extends JpaRepository<Audit,String>{List<Audit> findAll();}