package com.example.firstJobApp.job.impl;

import com.example.firstJobApp.job.Job;
import com.example.firstJobApp.job.JobService;
import com.example.firstJobApp.job.repository.JobRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Service;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;

import java.util.ArrayList;
import java.util.Iterator;
import java.util.List;
import java.util.Optional;


@Service
public class JobServiceImplement  implements JobService {

    @Autowired
    private JobRepository jobRepository;



    @Override
    public List<Job> findAll() {
        return jobRepository.findAll();
    }

    @Override
    public void createJob(Job job) {

        jobRepository.save(job);

    }

    @Override
    public Job getJobById(Long id) {
            //        for (Job job : jobs){
            //            if (job.getId().equals(id)){
            //                return job;
            //            }
            //        }
            //        return  null;
        Job user = jobRepository.findById(id).orElse(null);

        return user;
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
