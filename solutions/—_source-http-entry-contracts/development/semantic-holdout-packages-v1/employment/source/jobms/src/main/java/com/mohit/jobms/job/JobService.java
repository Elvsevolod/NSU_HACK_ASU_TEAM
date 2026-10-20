package com.mohit.jobms.job;

import com.mohit.jobms.job.dto.JobDTO;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
public interface JobService {




    List<JobDTO> findAll();
    void createJob(Job job);
    JobDTO getJobById(Long id);
    boolean deleteJobById(Long id);

    boolean updateJob(Long id , Job updatedJob);
}
