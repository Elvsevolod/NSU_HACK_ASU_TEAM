import java.util.*;class Api {String entry(){Map map=new HashMap();map.put(2>1,"ready");
  if("ready".equals(map.get(true))){return accepted();}return rejected();}
  String accepted(){return "ok";}String rejected(){return "bad";}}