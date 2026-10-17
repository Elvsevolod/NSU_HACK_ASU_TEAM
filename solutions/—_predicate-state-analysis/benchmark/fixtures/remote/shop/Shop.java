@RestController class Shop {
          RestTemplate http;
          @PostMapping("/orders") Receipt place(@RequestBody Request input) {
            return http.postForObject("http://ledger/charges", new HttpEntity(new Charge(input.sku)), Receipt.class);
          }
        }
        class Request { String sku; }
        class Receipt { String key; }
        class Charge { String key; Charge(String key) { this.key = key; } }