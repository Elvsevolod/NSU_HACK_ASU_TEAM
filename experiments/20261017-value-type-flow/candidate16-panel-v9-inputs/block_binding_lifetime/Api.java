import java.util.*;class Api{String key="outer";String inspect(){if(true){int key=1;}
  Map map=new HashMap();map.put(key,"ready");if("ready".equals(map.get("outer"))){return accepted();}return rejected();}
  String accepted(){return "ok";}String rejected(){return "bad";}}
  class Start{String entry(){return new Api().inspect();}}