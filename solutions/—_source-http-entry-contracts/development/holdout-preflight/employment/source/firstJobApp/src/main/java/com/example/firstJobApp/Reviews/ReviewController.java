package com.example.firstJobApp.Reviews;

import com.example.firstJobApp.Company.Company;
import org.springframework.http.HttpStatus;
import org.springframework.http.HttpStatusCode;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/companies/{companyId}")
public class ReviewController {

    private ReviewService reviewService;


    public ReviewController(ReviewService reviewService){

        this.reviewService = reviewService;

    }

    @GetMapping("/reviews")
    public ResponseEntity<List<Review>> getAllreview(@PathVariable  Long companyId) {

        return new ResponseEntity<>(reviewService.getAllreview(companyId), HttpStatus.OK);
    }

    @PostMapping("/reviews")
    public ResponseEntity<String>  addReview(@PathVariable Long companyId, @RequestBody Review review){

        return new ResponseEntity<>(reviewService.CreateReview(companyId ,review) , HttpStatus.OK);


    }

    @GetMapping("/reviews/{reviewId}")
    public  ResponseEntity<Review> getReview(@PathVariable Long companyId,
                                             @PathVariable Long reviewId){

        return new ResponseEntity<>(reviewService.getReview(companyId,reviewId),HttpStatus.OK);
    }


    @PutMapping("review/{reviewId}")
    public ResponseEntity<String> updateReview(@PathVariable Long companyId,
                                               @PathVariable Long reviewId,
                                               @RequestBody Review review){

          boolean isReviewUpdated =   reviewService.updateReview(companyId, reviewId, review);

          if (isReviewUpdated){

              return  new ResponseEntity<>("updated",HttpStatus.OK);
          }else {

              return new ResponseEntity<>("Not Updated",HttpStatus.NOT_FOUND);
          }

   }

    @DeleteMapping("review/{reviewId}")
    public  ResponseEntity<String> deleteReview(@PathVariable Long companyId, @PathVariable Long reviewId){

         if (reviewService.deleteReview(companyId, reviewId)){

             return  new ResponseEntity<>("deleted",HttpStatus.OK);
         }else {

             return new ResponseEntity<>(" not deleted",HttpStatus.INTERNAL_SERVER_ERROR);
         }


    }


}
