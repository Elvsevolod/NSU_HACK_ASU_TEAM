import java.util.*;import org.springframework.web.bind.annotation.*;
      class Item{public String title;}class Catalog{
        @GetMapping("/каталог")List<Item> показатьКаталог(){return new ArrayList<>();}
        @PostMapping("/заявки")Item создатьЗаявку(@RequestBody Item item){return item;}}