import java.util.*;class Api {String entry(){Map m=new HashMap();
    m.put(7,"integer");m.put("7","string");
    if("integer".equals(m.get(7))){return correct();}return wrong();}
    String correct(){return "correct";}String wrong(){return "wrong";}}