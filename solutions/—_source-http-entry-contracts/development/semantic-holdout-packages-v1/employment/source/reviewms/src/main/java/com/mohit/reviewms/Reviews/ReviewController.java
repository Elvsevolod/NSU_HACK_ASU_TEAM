package com.mohit.reviewms.Reviews;

import com.mohit.reviewms.Reviews.messaging.ReviewMessageProducer;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/reviews")
public class ReviewController {

    private ReviewService reviewService;

    private ReviewMessageProducer reviewMessageProducer;


    public ReviewController(ReviewService reviewService , ReviewMessageProducer reviewMessageProducer){

        this.reviewMessageProducer = reviewMessageProducer;
        this.reviewService = reviewService;

    }

    @GetMapping
    public ResponseEntity<List<Review>> getAllreview(@RequestParam Long companyId) {

        return new ResponseEntity<>(reviewService.getAllreview(companyId), HttpStatus.OK);
    }

    @PostMapping
    public ResponseEntity<String>  addReview(@RequestParam Long companyId, @RequestBody Review review){

        boolean isReviewSaved =   reviewService.CreateReview(companyId,review);
        if (isReviewSaved){
            reviewMessageProducer.sendMessage(review);
            return  new ResponseEntity<>("revieve added succesfully",HttpStatus.OK);
        }else {

            return new ResponseEntity<>("Review not added",HttpStatus.NOT_FOUND);
        }

    }

    @GetMapping("/{reviewId}")
    public  ResponseEntity<Review> getReview(@PathVariable Long reviewId){

        return new ResponseEntity<>(reviewService.getReview(reviewId),HttpStatus.OK);
    }


    @PutMapping("/{reviewId}")
    public ResponseEntity<String> updateReview(@PathVariable Long reviewId,
                                               @RequestBody Review review){

          boolean isReviewUpdated =   reviewService.updateReview( reviewId, review);

          if (isReviewUpdated){

              return  new ResponseEntity<>("updated",HttpStatus.OK);
          }else {

              return new ResponseEntity<>("Not Updated",HttpStatus.NOT_FOUND);
          }

   }

    @DeleteMapping("/{reviewId}")
    public  ResponseEntity<String> deleteReview( @PathVariable Long reviewId){

         if (reviewService.deleteReview( reviewId)){

             return  new ResponseEntity<>("deleted",HttpStatus.OK);
         }else {

             return new ResponseEntity<>(" not deleted",HttpStatus.INTERNAL_SERVER_ERROR);
         }


    }

    @GetMapping("/averageRating")
    public Double getAverageRating(@RequestParam Long companyId){

       List<Review> reviewList =  reviewService.getAllreview(companyId);
       return reviewList.stream().mapToDouble(Review::getRating).average().orElse(0);

    }

}
