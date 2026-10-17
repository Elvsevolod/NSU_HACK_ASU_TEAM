import org.springframework.web.client.RestTemplate;
  import org.springframework.web.client.HttpServerErrorException;
  class Client {RestTemplate rest;String entry(){try{
    rest.getForObject("http://stock/fail",String.class);return after();}
    catch(IllegalArgumentException failure){return wrong();}
    catch(HttpServerErrorException failure){return rejected();}}
    String after(){return "after";}String wrong(){return "wrong";}String rejected(){return "rejected";}}