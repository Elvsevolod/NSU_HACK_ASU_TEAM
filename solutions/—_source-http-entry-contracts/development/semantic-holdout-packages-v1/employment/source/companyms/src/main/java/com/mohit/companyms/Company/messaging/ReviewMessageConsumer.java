package com.mohit.companyms.Company.messaging;
import com.mohit.companyms.Company.CompanyService;
import com.mohit.companyms.Company.dto.ReviewMessageDto;
import org.springframework.amqp.rabbit.annotation.RabbitListener;
import org.springframework.stereotype.Service;


@Service
public class ReviewMessageConsumer {
    private final CompanyService companyService;

    public ReviewMessageConsumer(CompanyService companyService){
        this.companyService =companyService;
    }

    @RabbitListener(queues = "companyRatingQueue")
    public  void  consumeMessage(ReviewMessageDto reviewMessage){

        companyService.updateCompanyRating(reviewMessage);
    }


}
