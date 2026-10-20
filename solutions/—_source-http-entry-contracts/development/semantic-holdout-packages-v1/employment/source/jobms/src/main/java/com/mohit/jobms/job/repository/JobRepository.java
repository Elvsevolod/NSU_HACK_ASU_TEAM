package com.mohit.jobms.job.repository;


import com.mohit.jobms.job.Job;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

@Repository
public interface JobRepository  extends JpaRepository<Job,Long> {

}
