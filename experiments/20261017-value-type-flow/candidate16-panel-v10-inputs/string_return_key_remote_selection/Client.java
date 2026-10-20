import java.util.*;import org.springframework.web.client.RestTemplate;
 class Client {RestTemplate rest;String entry(){String part="mode-tail";Map map=new HashMap();
  map.put(part.substring(0,4),"ready");
  if("ready".equals(map.get("mode"))){return rest.getForObject("http://stock/alive",String.class);}
  return rest.getForObject("http://stock/wrong",String.class);}}