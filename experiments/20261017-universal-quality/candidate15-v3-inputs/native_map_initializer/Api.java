import java.util.*;class Api {String entry(){String value="ready";
    Map map=new HashMap(){{put("mode",value);}};
    if("ready".equals(map.get("mode"))){return accepted();}return rejected();}
    String accepted(){return "accepted";}String rejected(){return "rejected";}}