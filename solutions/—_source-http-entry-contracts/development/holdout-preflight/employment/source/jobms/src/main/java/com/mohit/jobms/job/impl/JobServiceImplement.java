package com.mohit.jobms.job.impl;

import com.mohit.jobms.job.Job;
import com.mohit.jobms.job.JobService;
import com.mohit.jobms.job.client.CompanyClient;
import com.mohit.jobms.job.client.ReviewClient;
import com.mohit.jobms.job.dto.JobDTO;
import com.mohit.jobms.job.external.Company;
import com.mohit.jobms.job.external.Review;
import com.mohit.jobms.job.mappper.JobMapper;
import com.mohit.jobms.job.repository.JobRepository;
import io.github.resilience4j.ratelimiter.annotation.RateLimiter;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;

import java.util.ArrayList;
import java.util.List;
import java.util.Optional;
import java.util.stream.Collectors;


@Service
public class JobServiceImplement  implements JobService {

    @Autowired
    private JobRepository jobRepository;

    @Autowired
    private  RestTemplate restTemplate;

    @Autowired
    private CompanyClient companyClient;

    @Autowired
    private ReviewClient reviewClient;

    int attempt= 0;


//    @CircuitBreaker(name = "companyBreaker", fallbackMethod = "companyBreakerFallbacks")
    // @Retry(name="companyBreaker", fallbackMethod = "companyBreakerFallbacks")

   @Override
   @RateLimiter(name = "companyBreaker", fallbackMethod = "companyBreakerFallbacks")
    public List<JobDTO> findAll() {

       System.out.println(" Attempt"+ ++attempt);
        List<Job> jobs = jobRepository.findAll();
     //   List<JobWithCompanyDTO> jobWithCompanyDTOs = new ArrayList<>();

       /* RestTemplate restTemplate = new RestTemplate();

        for (Job job: jobs){
            JobWithCompanyDTO jobWithCompanyDTO = new JobWithCompanyDTO();
            jobWithCompanyDTO.setJob(job);

            Company company = restTemplate.getForObject("http://localhost:8081/companies/"+ job.getCompany(), Company.class);

            jobWithCompanyDTO.setCompany(company);
            jobWithCompanyDTOs.add(jobWithCompanyDTO);

        }*/

        return  jobs.stream().map(this::convertToDto).collect(Collectors.toList());

    }

    public List<String> companyBreakerFallbacks(Exception e){
        List<String> list = new ArrayList<>();

        list.add("Dummy");
        return list;
    }


    private JobDTO convertToDto(Job job){
           // RestTemplate restTemplate = new RestTemplate();
            // we defined it into rest template concept ...


            //Company company = restTemplate.getForObject("http://COMPANYMS:8081/companies/"+ job.getCompany(), Company.class);
            Company company = companyClient.getCompany(job.getCompany());

//            ResponseEntity<List<Review>> reviewResponse = restTemplate.exchange("http://REVIEWMS:8083/reviews?companyId=" + job.getCompany(),
//                    HttpMethod.GET,
//                    null,
//                    new ParameterizedTypeReference<List<Review>>() {
//                    });
//
//            List<Review> reviews = reviewResponse.getBody();
            List<Review> reviews = reviewClient.getReviews(job.getCompany());

            JobDTO jobDTO = JobMapper.mapJobWithCompanyDto(job, company, reviews);
            //jobWithCompanyDTO.setCompany(company);
            return jobDTO;

    }

    @Override
    public void createJob(Job job) {

        jobRepository.save(job);

    }

    @Override
    public JobDTO getJobById(Long id) {

        Job job = jobRepository.findById(id).orElse(null);

       /* JobWithCompanyDTO jobWithCompanyDTO = new JobWithCompanyDTO();
        jobWithCompanyDTO.setJob(job);

        Company company = restTemplate.getForObject("http://COMPANYMS:8081/companies/"+ job.getCompany(), Company.class);

        jobWithCompanyDTO.setCompany(company);
          return jobWithCompanyDTO;

        */

        return convertToDto(job);




    }

    @Override
    public boolean deleteJobById(Long id) {
        //        Iterator<Job> iterator = jobs.iterator();
        //
        //        while (iterator.hasNext()){
        //            Job job = iterator.next();
        //            if(job.getId().equals(id)){
        //                iterator.remove();

        //                return  true;
        //            }
        //        }
        //
        //        return false;
        try {
            jobRepository.deleteById(id);
            return true;
        }
        catch (Exception e){
            return  false;

        }

    }

    @Override
    public boolean updateJob(Long id, Job updatedJob) {


        Optional<Job> jobOptional = jobRepository.findById(id);

        if (jobOptional.isPresent()){

            Job job = jobOptional.get();
            job.setTitle(updatedJob.getTitle());
            job.setDescription(updatedJob.getDescription());
            job.setLocation(updatedJob.getLocation());
            job.setMaxSalary(updatedJob.getMaxSalary());
            job.setMinSalary(updatedJob.getMinSalary());
           // jobRepository.save(job);
            return true;

        }

        return false;



    }


}
