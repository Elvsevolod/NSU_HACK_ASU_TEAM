package com.mohit.reviewms.Reviews.messaging;

import com.mohit.reviewms.Reviews.Review;
import com.mohit.reviewms.Reviews.dto.ReviewMessageDto;
import org.springframework.amqp.rabbit.core.RabbitTemplate;
import org.springframework.stereotype.Service;

@Service
public class ReviewMessageProducer {

    private final RabbitTemplate  rabbitTemplate;

    public ReviewMessageProducer(RabbitTemplate rabbitTemplate) {
        this.rabbitTemplate = rabbitTemplate;
    }

    public  void sendMessage(Review review){

        ReviewMessageDto reviewMessage = new ReviewMessageDto();
        reviewMessage.setId(review.getId());
        reviewMessage.setDescription(review.getDescription());
        reviewMessage.setCompanyId(review.getCompanyId());
        reviewMessage.setTitle(review.getTitle());
        reviewMessage.setRating(review.getRating());
        rabbitTemplate.convertAndSend("companyRatingQueue",reviewMessage);





    }



}

