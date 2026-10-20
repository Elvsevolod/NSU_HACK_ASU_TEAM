import org.springframework.stereotype.Component;
      import javax.annotation.PostConstruct;
      @Component class Counter{int revision;@PostConstruct void init(){revision=7;}
       int set(boolean flag){if(flag){revision=8;}else{revision=9;}revision=10;return revision;}
       int read(){return revision;}}
      class Patch{public boolean flag;}
      class Api{Counter counter;@PostMapping("/counter")int write(@RequestBody Patch input){return counter.set(input.flag);}
       @GetMapping("/counter")int read(){return counter.read();}}