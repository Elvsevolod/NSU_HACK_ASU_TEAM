import java.util.*;class Api {Store stock;AuditStore audit;String entry(){
  Map map=new HashMap();map.put("key"+7,"ready");
  if("ready".equals(map.get("key7"))){stock.findAll();return accepted();}
  audit.findAll();return rejected();}String accepted(){return "ok";}String rejected(){return "bad";}}
  @Entity @Table(name="items") class Item {@Id String id;}
  @Entity @Table(name="events") class Event {@Id String id;}
  interface Store extends JpaRepository<Item,String>{List<Item> findAll();}
  interface AuditStore extends JpaRepository<Event,String>{List<Event> findAll();}