import java.util.*;class Box<String>{String value;String getValue(){return value;}}
 class Api{String entry(){Box box=new Box();box.value='x';Map map=new HashMap();map.put(box.getValue(),"found");
 if("found".equals(map.get("x"))){return wrong();}return correct();}
 String correct(){return "ok";}String wrong(){return "bad";}}