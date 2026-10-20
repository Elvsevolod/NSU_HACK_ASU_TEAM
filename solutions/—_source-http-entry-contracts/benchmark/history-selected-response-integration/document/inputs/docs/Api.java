import java.util.*;import org.springframework.web.client.*;import org.springframework.http.*;
 import org.springframework.data.jpa.repository.JpaRepository;
 @Entity @Table(name="documents")class Document{@Id public String id;public int revision;public boolean approved;}
 class Approval{public String id;public int revision;public boolean approved;}
 interface Store extends JpaRepository<Document,String>{List<Document> findAll();Document findById(String id);Document save(Document value);}
 class DocumentController{Store store;RestTemplate rest;
  @GetMapping("/documents") List<Document> listDocuments(){return store.findAll();}
  @PostMapping("/documents/{id}/approve") ResponseEntity<Document> approveDocument(@PathVariable String id,@RequestBody Approval input){
   Document value=store.findById(id);if(value.revision!=input.revision){return new ResponseEntity<Document>(null,HttpStatus.CONFLICT);}
   value.approved=input.approved;value.revision++;store.save(value);
   try{rest.postForObject("http://audit/events",id,String.class);}catch(HttpServerErrorException failure){fallback();}
   return ResponseEntity.ok(value);}
  void fallback(){}
 }