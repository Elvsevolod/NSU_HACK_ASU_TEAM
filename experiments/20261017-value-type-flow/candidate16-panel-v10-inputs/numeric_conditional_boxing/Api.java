import java.util.*;class Api {String entry(){Map map=new HashMap();map.put(true?1:2L,"ready");
  if("ready".equals(map.get(1L)) && map.get(1)==null){return accepted();}return rejected();}
  String accepted(){return "ok";}String rejected(){return "bad";}}