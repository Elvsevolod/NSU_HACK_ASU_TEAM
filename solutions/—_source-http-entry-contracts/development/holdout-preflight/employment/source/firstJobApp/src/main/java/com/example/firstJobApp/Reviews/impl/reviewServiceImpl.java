package com.example.firstJobApp.Reviews.impl;

import com.example.firstJobApp.Company.Company;
import com.example.firstJobApp.Company.CompanyService;
import com.example.firstJobApp.Reviews.Review;
import com.example.firstJobApp.Reviews.ReviewService;
import com.example.firstJobApp.Reviews.repository.ReviewRepository;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
public class reviewServiceImpl implements ReviewService {

    private final ReviewRepository reviewRepository;

    private final CompanyService companyService;

    public reviewServiceImpl( ReviewRepository reviewRepository, CompanyService companyService){
        this.reviewRepository = reviewRepository;
        this.companyService = companyService;

    }

    @Override
    public String CreateReview(Long companyId, Review review) {
           Company company = companyService.getCompany(companyId);

           if (company!=null){
               review.setCompany(company);
               reviewRepository.save(review);
               return "Review CREATED";
           }
           else {
               return "Review not Created";
           }
    }


    @Override
    public Review getReview(Long companyId, Long reviewId) {

        List<Review> reviews = reviewRepository.findByCompanyId(companyId);

        return  reviews.stream().filter(review -> review.getId().equals(reviewId)).findFirst().orElse(null);

    }

    @Override
    public boolean deleteReview(Long companyId, Long reviewId) {

        if (companyService.getCompany(companyId) != null
                &&  reviewRepository.existsById(reviewId)){

            Review review = reviewRepository.findById(reviewId).orElse(null);

            assert review != null;
            Company company = review.getCompany();
             company.getReviews().remove(review);
             review.setCompany(null);
            companyService.updateCompany( companyId ,company);
            reviewRepository.deleteById(reviewId);
             return true;
        }else {
            return false;
        }
    }

    @Override
    public boolean updateReview(Long companyId, Long reviewId , Review updatedReview) {

        List<Review>  reviews = reviewRepository.findByCompanyId(companyId);

        if (companyService.getCompany(companyId) != null){
            updatedReview.setCompany(companyService.getCompany(companyId));

            updatedReview.setId(reviewId);
            reviewRepository.save(updatedReview);
            return  true;
        }
        else {
            return  false;
        }

    }

    @Override
    public List<Review> getAllreview(Long companyId) {

        return reviewRepository.findByCompanyId(companyId);
    }
}
