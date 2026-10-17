import java.util.*;class Api {
    @GetMapping("/settings") Map load(){Map flags=new HashMap();flags.put("mode","ready");return flags;}
    @PostMapping("/publish") String publish(@RequestBody Input input){
      if("ready".equals(input.mode)){return accepted();}return rejected();}
    String accepted(){return "accepted";}String rejected(){return "rejected";}}
    class Input {public String mode;}