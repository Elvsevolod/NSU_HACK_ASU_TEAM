import java.util.*;import org.springframework.web.client.RestTemplate;
        class Approval{RestTemplate rest;String entry(String id,List<String> unknown,boolean inspectOnly){
        String prefix=rest.getForObject("http://warehouse/equipment/"+id,String.class);
        if(inspectOnly){for(String item:unknown){String projected=item;}return prefix;}
        return rest.postForObject("http://warehouse/reserve/"+id,null,String.class);}}