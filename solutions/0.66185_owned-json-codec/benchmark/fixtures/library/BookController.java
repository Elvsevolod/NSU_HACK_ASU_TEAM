import org.springframework.web.bind.annotation.*;
    import org.springframework.beans.factory.annotation.Autowired;
    @RestController class BookController {
      @Autowired BookStore repository;
      @GetMapping("/books/{key}") String lookup(@PathVariable String key) {
        Book found = repository.findByKey(key);
        if (found == null) { return missing(); }
        return available(found);
      }
      String missing() { return "absent"; }
      String available(Book found) { return found.title; }
      @GetMapping("/catalog") String search(String query) { return "matches"; }
      @PostMapping("/books") Book add(@RequestBody Book input) { repository.save(input); return input; }
    }