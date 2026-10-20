package com.example.firstJobApp.job.repository;

import com.example.firstJobApp.job.Job;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

@Repository
public interface JobRepository  extends JpaRepository<Job,Long> {

}
