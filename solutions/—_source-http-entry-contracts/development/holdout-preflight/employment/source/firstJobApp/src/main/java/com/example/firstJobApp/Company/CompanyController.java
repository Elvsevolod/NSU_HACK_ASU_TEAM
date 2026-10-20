package com.example.firstJobApp.Company;


import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Controller;
import org.springframework.stereotype.Service;
import org.springframework.web.bind.annotation.*;

import java.awt.event.ComponentAdapter;
import java.util.List;

@Controller
@RequestMapping("/companies")
public class CompanyController {

    @Autowired
    CompanyService service;

    @PostMapping
    public ResponseEntity<Company> createCompany(@RequestBody Company  company){

          Company CreatedCompany = service.createCompany(company);
          return new ResponseEntity<>(CreatedCompany , HttpStatus.CREATED);
    }

    @GetMapping("/{id}")
    public   ResponseEntity<Company>  getCompany( @PathVariable  Long id){

        return  new ResponseEntity<>(service.getCompany(id),HttpStatus.OK);
    }

    @DeleteMapping("/{id}")
    public ResponseEntity<String>  deleteCompany( @PathVariable  Long id){
         boolean deleteCompanyStatus = service.deleteCompany(id);

         if( deleteCompanyStatus){
             return  new ResponseEntity<>("Delete succefully" , HttpStatus.OK);
         }else {
             return  new ResponseEntity<>("Deleted is not succesfully", HttpStatus.CONFLICT);
         }


    }

    @PutMapping("/{id}")
    public ResponseEntity<String>  updateCompany(@PathVariable Long id, @RequestBody Company company){



        return  new  ResponseEntity<>(service.updateCompany(id,company), HttpStatus.OK);


    }

    @GetMapping
    public ResponseEntity<List<Company>> getAllCompany(){

        return new ResponseEntity<>(service.getAllCompany(),HttpStatus.OK);
    }







}
