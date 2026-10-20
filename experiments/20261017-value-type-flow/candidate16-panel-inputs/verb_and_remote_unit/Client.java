import org.springframework.web.client.RestTemplate;class Client {RestTemplate rest;String entry(){
   return rest.postForObject("http://stock/records","payload",String.class);}}