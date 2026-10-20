package com.example.firstJobApp.Company.repository;


import com.example.firstJobApp.Company.Company;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

@Repository
public interface CompanyRepository extends JpaRepository<Company,Long> {




}
