package com.mohit.jobms.job;


import com.mohit.jobms.job.dto.JobDTO;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/jobs")
public class JobController {

    @Autowired
    private JobService jobService;

    @GetMapping
    public ResponseEntity<List<JobDTO>> findAll(){

        return ResponseEntity.ok(jobService.findAll());
    }

    @PostMapping
    public ResponseEntity<String> createJob(@RequestBody Job job){

        jobService.createJob(job);

        return new ResponseEntity<>("Job added succesfully",HttpStatus.CREATED);
    }

    @GetMapping("/{id}")
    public ResponseEntity<JobDTO> getJob(@PathVariable Long id){

        JobDTO job = jobService.getJobById(id);

        if(job != null){
             return  new ResponseEntity<>(job, HttpStatus.OK);

        }
        return new ResponseEntity<>(HttpStatus.NOT_FOUND);
    }

    @DeleteMapping("/{id}")
    public ResponseEntity<String> deleteJob(@PathVariable Long id){

        boolean deleted = jobService.deleteJobById(id);

        if (deleted)
            return new  ResponseEntity<>("deletion succesfull",HttpStatus.NOT_FOUND);

        return new ResponseEntity<>(HttpStatus.NOT_FOUND);
    }

    @PutMapping("/{id}")
    public ResponseEntity<String> updateJob(@PathVariable Long id, @RequestBody Job updatedJob){
        boolean updated = jobService.updateJob(id, updatedJob);
        if (updated)
            return new  ResponseEntity<>("Job updated succesfully", HttpStatus.OK);
        return new ResponseEntity<>(HttpStatus.NOT_FOUND);

    }




}
