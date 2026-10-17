import java.util.*;class Item{String getKey(){return "known";}}
 class Api{String entry(){Map map=new HashMap();for(Item item:Arrays.asList(new Item())){
  map.put(item.getKey(),"ready");}if("ready".equals(map.get("known"))){return accepted();}return rejected();}
  String accepted(){return "ok";}String rejected(){return "bad";}}