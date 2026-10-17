import java.util.*;class Api {
    @PostMapping("/update") String update(@RequestBody Map<String,String> input){input.put("mode","changed");return "ok";}}