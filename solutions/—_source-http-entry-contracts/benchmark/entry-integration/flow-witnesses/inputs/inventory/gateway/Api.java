import java.util.*;import org.springframework.web.client.RestTemplate;
 class ProductView{public String id;public String category;public int revision;public int quantity;}
 class Category{public String code;}
 class ProductRequest{public String id;public int revision;}
 class InventoryGateway{RestTemplate rest;
  @GetMapping("/inventory") List<ProductView> listProducts(){
   ProductView[] received=rest.getForObject("http://warehouse/products",ProductView[].class);
   List<ProductView> products=new ArrayList<>(Arrays.asList(received));Set<String> codes=new HashSet<>();
   Map<String,List<ProductView>> groups=new HashMap<>();
   for(ProductView product:products){codes.add(product.category);
    if(groups.get(product.category)==null){groups.put(product.category,new ArrayList<>());}groups.get(product.category).add(product);}
   Category[] categories=rest.postForObject("http://catalog/categories",new ArrayList<>(codes),Category[].class);
   Map<String,Category> categoryMap=new HashMap<>();for(Category category:categories){categoryMap.put(category.code,category);}
   for(String code:groups.keySet()){if(categoryMap.get(code)==null){products.removeAll(groups.get(code));}}
   return products;}
  @PostMapping("/inventory/reserve") ProductView reserveProduct(@RequestBody ProductRequest input){
   return rest.postForObject("http://warehouse/products/"+input.id+"/reserve",input,ProductView.class);}}
