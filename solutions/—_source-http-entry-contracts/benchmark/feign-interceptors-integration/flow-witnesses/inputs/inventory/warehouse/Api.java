import java.util.*;import org.springframework.data.jpa.repository.JpaRepository;import org.springframework.http.*;
 @Entity @Table(name="products")class Product{@Id public String id;public String category;public int revision;public int quantity;}
 class ProductRequest{public String id;public int revision;}
 interface Stock extends JpaRepository<Product,String>{Product findById(String id);Product save(Product product);}
 class StockController{Stock stock;
  @GetMapping("/products") List<Product> listProducts(){return Arrays.asList(stock.findById("SKU7"),stock.findById("SKU8"),stock.findById("SKU9"));}
  @PostMapping("/products/{id}/reserve") ResponseEntity<Product> reserveProduct(@PathVariable String id,@RequestBody ProductRequest input){
   Product product=stock.findById(id);if(product.revision!=input.revision){return new ResponseEntity<Product>(null,HttpStatus.CONFLICT);}
   product.quantity--;product.revision++;stock.save(product);return ResponseEntity.ok(product);}}
