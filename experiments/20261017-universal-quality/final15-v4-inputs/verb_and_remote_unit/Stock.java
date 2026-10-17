class Api {@GetMapping("/records") String read(){return "get";}
   @PostMapping("/records") String write(@RequestBody String body){return accepted();}
   String accepted(){return "post";}}