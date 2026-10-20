package com.mohit.companyms.Company.impl;

import com.mohit.companyms.Company.Company;
import com.mohit.companyms.Company.CompanyService;
import com.mohit.companyms.Company.client.ReviewClient;
import com.mohit.companyms.Company.dto.ReviewMessageDto;
import com.mohit.companyms.Company.repository.CompanyRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.Optional;

@Service
public class companyServiceImplement implements CompanyService {

    @Autowired
    private CompanyRepository companyRepository;

    @Autowired
    private ReviewClient reviewClient;



    @Override
    public Company createCompany(Company company) {
        Company companies = new Company();

        companies.setName(company.getName());
        companies.setDescription(company.getDescription());
        return companyRepository.save(companies);
    }

    @Override
    public Company getCompany(Long id) {

        return companyRepository.findById(id).orElse(null);
    }

    @Override
    public boolean deleteCompany(Long id) {
        try {
            companyRepository.deleteById(id);
            return true;
        }
        catch (Exception e){
            return  false;
        }

    }

    @Override
    public String updateCompany(Long id ,Company company) {

        Optional<Company> existingCompany = companyRepository.findById(id);

        if (existingCompany.isPresent()){

            Company com = existingCompany.get();

            com.setDescription(company.getDescription());
            com.setName(company.getName());

            return "Update Succesfully" ;
        }
        else {
            return  "problem occured while saving";
        }

    }

    @Override
    public List<Company> getAllCompany() {
        return companyRepository.findAll();
    }

    @Override
    public void updateCompanyRating(ReviewMessageDto reviewMessage) {

        System.out.println(reviewMessage.getDescription());
        Company company = companyRepository.findById(reviewMessage.getCompanyId()).orElseThrow(() -> new RuntimeException(" id not found here "+ reviewMessage.getCompanyId()));
        double averageRating = reviewClient.getAverageRatingForCompany(reviewMessage.getCompanyId());
        System.out.println(averageRating);
        company.setRating(averageRating);
        companyRepository.save(company);

    }
}
