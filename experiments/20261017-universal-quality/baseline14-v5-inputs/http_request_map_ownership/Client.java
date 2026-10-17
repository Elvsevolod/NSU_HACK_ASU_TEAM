import java.util.*;import org.springframework.web.client.RestTemplate;
    class Client {RestTemplate rest;String entry(){Map input=new HashMap();input.put("mode","original");
      rest.postForObject("http://stock/update",input,String.class);
      if("original".equals(input.get("mode"))){return accepted();}return rejected();}
      String accepted(){return "accepted";}String rejected(){return "rejected";}}