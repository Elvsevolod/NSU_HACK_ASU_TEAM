package com.mohit.jobms.job.mappper;

import com.mohit.jobms.job.Job;
import com.mohit.jobms.job.dto.JobDTO;
import com.mohit.jobms.job.external.Company;
import com.mohit.jobms.job.external.Review;

import java.util.List;

public class JobMapper {

    public  static JobDTO mapJobWithCompanyDto(Job job , Company company , List<Review> reviews){

        JobDTO jobDTO = new JobDTO();

        jobDTO.setId(job.getId());
        jobDTO.setDescription(job.getDescription());
        jobDTO.setLocation(job.getLocation());
        jobDTO.setTitle(job.getTitle());
        jobDTO.setMaxSalary(job.getMaxSalary());
        jobDTO.setMinSalary(job.getMinSalary());
        jobDTO.setCompany(company);

        jobDTO.setReview(reviews);
        return jobDTO;

    }


}
