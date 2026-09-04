package com.clinevo.inbox.queue;

import com.clinevo.inbox.entity.JobStatus;
import com.clinevo.inbox.entity.ProcessingJob;
import com.clinevo.inbox.repository.ProcessingJobRepository;
import com.clinevo.inbox.service.JobService;
import jakarta.annotation.PostConstruct;
import jakarta.annotation.PreDestroy;
import lombok.RequiredArgsConstructor;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import java.util.List;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;

@Component
@RequiredArgsConstructor
public class JobWorker {

    private static final Logger log = LoggerFactory.getLogger(JobWorker.class);

    private final JobQueue jobQueue;
    private final JobService jobService;
    private final ProcessingJobRepository jobRepository;

    @Value("${queue.worker.enabled:true}")
    private boolean workerEnabled;

    @Value("${queue.worker.concurrency:1}")
    private int concurrency;

    private ExecutorService executor;
    private final AtomicBoolean running = new AtomicBoolean(false);

    @PostConstruct
    public void start() {
        if (!workerEnabled) {
            log.info("JobWorker is disabled via configuration.");
            return;
        }

        running.set(true);
        executor = Executors.newFixedThreadPool(concurrency, r -> {
            Thread t = new Thread(r, "job-worker");
            t.setDaemon(true);
            return t;
        });

        for (int i = 0; i < concurrency; i++) {
            executor.submit(this::workerLoop);
        }

        log.info("JobWorker started with concurrency {}", concurrency);

        // Recover pending jobs from database on startup
        try {
            List<ProcessingJob> pendingJobs = jobRepository.findByStatus(JobStatus.QUEUED);
            if (!pendingJobs.isEmpty()) {
                log.info("Startup recovery: Enqueueing {} pending QUEUED jobs from database.", pendingJobs.size());
                for (ProcessingJob pj : pendingJobs) {
                    jobQueue.enqueue(pj.getId());
                }
            }
        } catch (Exception e) {
            log.warn("Could not recover pending jobs on startup: {}", e.getMessage());
        }
    }

    @PreDestroy
    public void stop() {
        running.set(false);
        if (executor != null) {
            executor.shutdownNow();
            try {
                if (!executor.awaitTermination(5, TimeUnit.SECONDS)) {
                    log.warn("JobWorker executor did not terminate in time.");
                }
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
            }
        }
        log.info("JobWorker stopped.");
    }

    private void workerLoop() {
        while (running.get() && !Thread.currentThread().isInterrupted()) {
            try {
                Long jobId = jobQueue.poll(1, TimeUnit.SECONDS);
                if (jobId != null) {
                    jobService.processJob(jobId);
                } else {
                    // Check if any QUEUED jobs are in database and process
                    List<ProcessingJob> queued = jobRepository.findByStatus(JobStatus.QUEUED);
                    for (ProcessingJob pj : queued) {
                        if (!running.get()) break;
                        jobService.processJob(pj.getId());
                    }
                }
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
                break;
            } catch (Exception e) {
                log.error("Unexpected error in JobWorker loop: {}", e.getMessage(), e);
            }
        }
    }
}
