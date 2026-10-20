package com.mohit.reviewms.Reviews;

import org.springframework.stereotype.Service;

import java.util.List;

@Service
public interface ReviewService {



    boolean CreateReview(Long companyId, Review review);


    Review getReview( Long reviewId);


    boolean  deleteReview(Long reviewId);

    boolean updateReview( Long  reviewId, Review updatedReview);

    List<Review> getAllreview(Long companyId);






}
