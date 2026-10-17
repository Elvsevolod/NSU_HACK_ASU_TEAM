import org.springframework.web.bind.annotation.*;import org.springframework.web.client.RestTemplate;import java.util.Map;
@RestController class Gateway {
 @PostMapping("/make") Object make(){return new RestTemplate().postForObject("http://items/items",Map.of("quantity",6),Object.class);}
 @GetMapping("/load/{id}") Object load(@PathVariable String id){return new RestTemplate().getForObject("http://items/items/"+id,Object.class);}
}