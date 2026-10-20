import java.util.*;import org.springframework.web.client.RestTemplate;
 import org.springframework.http.*;import com.fasterxml.jackson.databind.ObjectMapper;
 class DocumentView{public String id;public int revision;public boolean approved;}
 class Approval{public String id;public int revision;public boolean approved;}
 class PortalGateway{RestTemplate rest;
  <T>T decode(String text,Class<T> type){return new ObjectMapper().readValue(text,type);}
  @GetMapping("/library") List<DocumentView> listDocuments(){
   String text=rest.getForObject("http://docs/documents",String.class);
   return Arrays.asList(decode(text,DocumentView[].class));}
  @PostMapping("/library/approve") DocumentView approveDocument(@RequestBody Approval input){
   return rest.postForObject("http://docs/documents/"+input.id+"/approve",input,DocumentView.class);}
 }