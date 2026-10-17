import org.springframework.web.bind.annotation.*;
import org.springframework.web.client.RestTemplate;
import org.springframework.http.*;
import java.util.Map;
import java.util.UUID;
class Upload {String title;int quantity;}
@RestController class Portal {
 RestTemplate client=new RestTemplate();
 @PostMapping("/artifacts") Object create(@RequestBody Upload upload){return client.exchange("http://catalog/items",HttpMethod.POST,new HttpEntity<>(upload),Map.class).getBody();}
 @GetMapping("/artifacts/{id}") Object read(@PathVariable UUID id){return client.getForObject("http://catalog/items/"+id,Map.class);}
}