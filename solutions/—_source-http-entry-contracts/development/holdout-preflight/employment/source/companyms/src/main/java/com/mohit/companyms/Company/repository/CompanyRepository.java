package com.mohit.companyms.Company.repository;



import com.mohit.companyms.Company.Company;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

@Repository
public interface CompanyRepository extends JpaRepository<Company,Long> {




}
