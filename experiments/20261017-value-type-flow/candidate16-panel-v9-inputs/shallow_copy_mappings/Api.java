import java.util.*;class Api {String entry(){
   Map original=new HashMap();original.put("mode","ready");Map copied=new HashMap(original);
   if("ready".equals(copied.get("mode"))){return ready();}return lost();}
   String ready(){return "ready";}String lost(){return "lost";}}