package com.mohit.reviewms.Reviews.impl;


import com.mohit.reviewms.Reviews.Review;
import com.mohit.reviewms.Reviews.ReviewService;
import com.mohit.reviewms.Reviews.repository.ReviewRepository;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
public class reviewServiceImpl implements ReviewService {

    private final ReviewRepository reviewRepository;



    public reviewServiceImpl( ReviewRepository reviewRepository){
        this.reviewRepository = reviewRepository;

    }

    @Override
    public boolean CreateReview(Long companyId, Review review) {


           if (companyId!=null){
               review.setCompanyId(companyId);
               reviewRepository.save(review);
               return true;
           }
           else {
               return false;
           }
    }


    @Override
    public Review getReview( Long reviewId) {

      return  reviewRepository.findById(reviewId).orElse(null);

    }

    @Override
    public boolean deleteReview(Long reviewId) {

        Review review = reviewRepository.findById(reviewId).orElse(null);

        if ( review != null){

            reviewRepository.delete(review);
             return true;
        }else {
            return false;
        }
    }

    @Override
    public boolean updateReview( Long reviewId , Review updatedReview) {
        Review review = reviewRepository.findById(reviewId).orElse(null);
        if (review != null){
            review.setTitle(updatedReview.getTitle());
            review.setDescription(updatedReview.getDescription());
            review.setRating(updatedReview.getRating());

            review.setCompanyId(updatedReview.getCompanyId());
            reviewRepository.save(review);
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
