package com.example.firstJobApp.job;

import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.List;

@Service
public interface JobService {




    List<Job> findAll();
    void createJob(Job job);
    Job getJobById(Long id);
    boolean deleteJobById(Long id);

    boolean updateJob(Long id , Job updatedJob);
}
