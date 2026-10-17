class Api {@GetMapping("/alive") String alive(){return "ok";}
  @GetMapping("/wrong") String wrong(){return "bad";}}