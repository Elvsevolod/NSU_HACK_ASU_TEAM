@RestController class Ledger {
          Store repository;
          @PostMapping("/charges") Charge charge(@RequestBody Charge input) { repository.save(input); return input; }
          @GetMapping("/charges/{key}") Charge lookup(@PathVariable String key) { return repository.findByKey(key); }
        }
        @Entity @Table(name="charges") class Charge { @Id public String key; }
        interface Store extends JpaRepository<Charge,String> { Charge save(Charge item); Charge findByKey(String key); }