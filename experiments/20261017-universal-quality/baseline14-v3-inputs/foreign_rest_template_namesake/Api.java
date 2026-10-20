import external.library.RestTemplate;
    class Api {@GetMapping("/items") String list(){return "wrong";}}
    class Client {RestTemplate rest;Object entry(){return rest.getForObject("http://service/items",Object.class);}}