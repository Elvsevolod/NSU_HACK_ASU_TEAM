package com.example.firstJobApp.Reviews;

import com.example.firstJobApp.Company.Company;
import com.example.firstJobApp.Reviews.repository.ReviewRepository;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
public interface ReviewService {



    String CreateReview(Long companyId, Review review);


    Review getReview(Long companyId, Long reviewId);


    boolean  deleteReview(Long companyId , Long reviewId);

    boolean updateReview(Long companyId , Long  reviewId, Review updatedReview);

    List<Review> getAllreview(Long companyId);






}
