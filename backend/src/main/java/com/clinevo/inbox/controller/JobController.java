package com.clinevo.inbox.controller;

import com.clinevo.inbox.dto.ApiResponse;
import com.clinevo.inbox.dto.JobDto;
import com.clinevo.inbox.service.JobService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/jobs")
@RequiredArgsConstructor
@CrossOrigin(origins = "*")
public class JobController {

    private final JobService jobService;

    @GetMapping
    public ResponseEntity<ApiResponse<List<JobDto>>> getAllJobs() {
        List<JobDto> jobs = jobService.getAllJobs();
        return ResponseEntity.ok(ApiResponse.ok(jobs));
    }

    @GetMapping("/{id}")
    public ResponseEntity<ApiResponse<JobDto>> getJobById(@PathVariable Long id) {
        JobDto job = jobService.getJobById(id);
        return ResponseEntity.ok(ApiResponse.ok(job));
    }

    @PostMapping("/{id}/retry")
    public ResponseEntity<ApiResponse<JobDto>> retryJob(@PathVariable Long id) {
        JobDto retried = jobService.retryJob(id);
        return ResponseEntity.ok(ApiResponse.ok("Job re-enqueued for retry", retried));
    }
}
