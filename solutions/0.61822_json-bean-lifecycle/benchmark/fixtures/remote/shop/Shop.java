import org.springframework.web.client.RestTemplate;import org.springframework.web.client.RestOperations;@RestController class Shop {
          RestTemplate http;
          @PostMapping("/orders") Receipt place(@RequestBody Request input) {
            return http.postForObject("http://ledger/charges", new HttpEntity(new Charge(input.sku)), Receipt.class);
          }
        }
        class Request { public String sku; }
        class Receipt { public String key; }
        class Charge { public String key; Charge(String key) { this.key = key; } }