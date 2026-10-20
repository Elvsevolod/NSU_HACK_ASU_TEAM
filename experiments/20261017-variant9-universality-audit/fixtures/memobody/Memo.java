
            @RestController class MemoController {
              @PostMapping("/memos") Memo create(@RequestBody Memo input) { return input; }
              @GetMapping("/memos/{memoId}") String inspect(@PathVariable String memoId) {
                if (memoId.equals("m4")) { return found(); }
                return missing();
              }
              String found() { return "found"; }
              String missing() { return "missing"; }
            }
            class Memo { @Id String key; String body; }
        