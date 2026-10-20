import java.util.*;import org.springframework.web.client.RestTemplate;
  import org.springframework.core.ParameterizedTypeReference;import org.springframework.http.HttpMethod;
  class Client {RestTemplate rest;String entry(){Box<Map<String,String>> value=rest.exchange(
    "http://stock/item",HttpMethod.GET,null,new ParameterizedTypeReference<Box<Map<String,String>>>(){}).getBody();
    if("known".equals(value.payload.get("id"))){return accepted();}return rejected();}
    String accepted(){return "accepted";}String rejected(){return "rejected";}}