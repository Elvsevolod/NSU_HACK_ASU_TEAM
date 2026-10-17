import org.springframework.web.bind.annotation.*;
    import org.springframework.beans.factory.annotation.Autowired;
    @RestController class StockController {
      @Autowired StockWorker worker;
      @PostMapping("/reserve") Reservation reserve(@RequestBody StockRequest input) {
        if (input.enabled) { return worker.accept(input.key); }
        return worker.reject(input.key);
      }
      @GetMapping("/inventory") String inspect(String key) { return worker.status(key); }
      @PostMapping("/release") Reservation release(@RequestBody StockRequest input) { return worker.reject(input.key); }
    }