package com.example.firstJobApp.Company;

import org.springframework.stereotype.Service;

import java.util.List;

@Service
public interface CompanyService {

    Company createCompany(Company company);

    Company getCompany(Long id);

    boolean  deleteCompany(Long id);

    String updateCompany(Long id,Company company);

    List<Company> getAllCompany();




}
