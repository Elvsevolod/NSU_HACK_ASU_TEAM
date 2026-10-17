import java.util.*;import java.util.stream.Collectors;class Api{String entry(){Map map=new HashMap();
  List<String> values=Arrays.asList("known");values.stream().map(key->{map.put(key,"ready");return key;})
  .collect(Collectors.toList());if("ready".equals(map.get("known"))){return accepted();}return rejected();}
  String accepted(){return "ok";}String rejected(){return "bad";}}