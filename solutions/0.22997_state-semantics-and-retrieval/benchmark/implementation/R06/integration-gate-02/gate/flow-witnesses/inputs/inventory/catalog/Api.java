import java.util.*;import org.springframework.data.jpa.repository.JpaRepository;
 @Entity @Table(name="categories")class Category{@Id public String code;}
 interface Categories extends JpaRepository<Category,String>{List<Category> findByCodeIn(List<String> codes);}
 class CategoryController{Categories categories;@PostMapping("/categories")List<Category> lookup(@RequestBody List<String> codes){return categories.findByCodeIn(codes);}}
