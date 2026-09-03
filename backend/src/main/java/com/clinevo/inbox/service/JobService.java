package com.clinevo.inbox.service;

import com.clinevo.inbox.client.AIClient;
import com.clinevo.inbox.dto.JobDto;
import com.clinevo.inbox.dto.ai.AIProcessRequestDto;
import com.clinevo.inbox.dto.ai.AIProcessResponseDto;
import com.clinevo.inbox.entity.*;
import com.clinevo.inbox.exception.ResourceNotFoundException;
import com.clinevo.inbox.queue.JobQueue;
import com.clinevo.inbox.repository.AttachmentRepository;
import com.clinevo.inbox.repository.EmailRepository;
import com.clinevo.inbox.repository.ProcessingJobRepository;
import lombok.RequiredArgsConstructor;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.Instant;
import java.util.List;

@Service
@RequiredArgsConstructor
public class JobService {

    private static final Logger log = LoggerFactory.getLogger(JobService.class);

    private final ProcessingJobRepository jobRepository;
    private final AttachmentRepository attachmentRepository;
    private final EmailRepository emailRepository;
    private final JobQueue jobQueue;
    private final AuditService auditService;
    private final AIClient aiClient;
    private final ResultService resultService;

    @Transactional(readOnly = true)
    public JobDto getJobById(Long jobId) {
        ProcessingJob job = jobRepository.findById(jobId)
                .orElseThrow(() -> new ResourceNotFoundException("Job not found with id: " + jobId));
        return toDto(job);
    }

    @Transactional(readOnly = true)
    public List<JobDto> getAllJobs() {
        return jobRepository.findAll().stream()
                .map(this::toDto)
                .toList();
    }

    @Transactional
    public JobDto retryJob(Long jobId) {
        ProcessingJob job = jobRepository.findById(jobId)
                .orElseThrow(() -> new ResourceNotFoundException("Job not found with id: " + jobId));

        job.setStatus(JobStatus.QUEUED);
        job.setErrorCode(null);
        job.setErrorMessage(null);
        job = jobRepository.save(job);

        Long emailId = job.getAttachment() != null && job.getAttachment().getEmail() != null
                ? job.getAttachment().getEmail().getId() : null;

        auditService.log(emailId, jobId, ActorType.SYSTEM, "SYSTEM", "JOB_MANUAL_RETRY", null, null,
                String.format("{\"jobId\":%d,\"retryCount\":%d}", jobId, job.getRetryCount()));

        jobQueue.enqueue(jobId);

        return toDto(job);
    }

    @Transactional
    public void processJob(Long jobId) {
        log.info("Job execution started for Job ID: {}", jobId);

        ProcessingJob job = jobRepository.findById(jobId).orElse(null);
        if (job == null) {
            log.warn("Job ID: {} not found in database. Skipping.", jobId);
            return;
        }

        Attachment attachment = job.getAttachment();
        Email email = attachment != null ? attachment.getEmail() : null;
        Long emailId = email != null ? email.getId() : null;

        // Transition: QUEUED -> PROCESSING
        job.setStatus(JobStatus.PROCESSING);
        job.setStartedAt(Instant.now());
        jobRepository.save(job);

        if (attachment != null) {
            attachment.setStatus(AttachmentStatus.PROCESSING);
            attachmentRepository.save(attachment);
        }

        auditService.log(emailId, jobId, ActorType.AI, "AI_CLIENT", "AI_STARTED", null, null,
                String.format("{\"filename\":\"%s\",\"startedAt\":\"%s\"}",
                        attachment != null ? attachment.getFilename() : "unknown", job.getStartedAt()));

        try {
            // Build AIProcessRequest
            AIProcessRequestDto request = AIProcessRequestDto.builder()
                    .jobId(jobId)
                    .email(email != null ? AIProcessRequestDto.EmailContext.builder()
                            .emailId(email.getId())
                            .sender(email.getSenderEmail())
                            .subject(email.getSubject())
                            .body(email.getBody())
                            .build() : null)
                    .document(AIProcessRequestDto.DocumentContext.builder()
                            .attachmentId(attachment != null ? attachment.getId() : null)
                            .filename(attachment != null ? attachment.getFilename() : "document.pdf")
                            .contentType(attachment != null ? attachment.getContentType() : "application/pdf")
                            .storageReference(attachment != null ? attachment.getStorageReference() : "")
                            .build())
                    .build();

            // Invoke FastAPI AI pipeline
            AIProcessResponseDto response = aiClient.process(request);

            if (response == null || !Boolean.TRUE.equals(response.getValidationPassed())) {
                throw new RuntimeException("AI pipeline validation failed or produced empty response");
            }

            // Persist entire AI result graph atomically
            resultService.persistResult(jobId, response);

        } catch (Exception e) {
            log.error("AI processing for Job ID: {} failed: {}", jobId, e.getMessage(), e);
            auditService.log(emailId, jobId, ActorType.AI, "AI_CLIENT", "AI_FAILED", null, null,
                    String.format("{\"error\":\"%s\"}", e.getMessage()));
            handleJobFailure(job, e);
        }
    }

    private void handleJobFailure(ProcessingJob job, Exception e) {
        Attachment attachment = job.getAttachment();
        Long emailId = (attachment != null && attachment.getEmail() != null) ? attachment.getEmail().getId() : null;

        int newRetryCount = job.getRetryCount() + 1;
        job.setRetryCount(newRetryCount);
        job.setErrorCode(e.getClass().getSimpleName());
        job.setErrorMessage(e.getMessage() != null ? e.getMessage().substring(0, Math.min(1900, e.getMessage().length())) : "Error");

        if (newRetryCount < job.getMaxRetries()) {
            job.setStatus(JobStatus.RETRYING);
            jobRepository.save(job);
            auditService.log(emailId, job.getId(), ActorType.SYSTEM, "SYSTEM", "JOB_RETRYING", null, null,
                    String.format("{\"retryCount\":%d,\"maxRetries\":%d}", newRetryCount, job.getMaxRetries()));
            // Re-enqueue for retry
            jobQueue.enqueue(job.getId());
        } else {
            job.setStatus(JobStatus.REVIEW_REQUIRED);
            jobRepository.save(job);

            if (attachment != null) {
                attachment.setStatus(AttachmentStatus.FAILED);
                attachmentRepository.save(attachment);
                if (attachment.getEmail() != null) {
                    attachment.getEmail().setStatus(EmailStatus.REVIEW_REQUIRED);
                    emailRepository.save(attachment.getEmail());
                }
            }

            auditService.log(emailId, job.getId(), ActorType.SYSTEM, "SYSTEM", "VALIDATION_FAILED", null, null,
                    String.format("{\"error\":\"%s\",\"retriesExhausted\":true}", job.getErrorMessage()));
        }
    }

    private JobDto toDto(ProcessingJob job) {
        Attachment att = job.getAttachment();
        Long emailId = (att != null && att.getEmail() != null) ? att.getEmail().getId() : null;
        String filename = att != null ? att.getFilename() : null;

        return JobDto.builder()
                .id(job.getId())
                .attachmentId(att != null ? att.getId() : null)
                .emailId(emailId)
                .filename(filename)
                .status(job.getStatus())
                .retryCount(job.getRetryCount())
                .maxRetries(job.getMaxRetries())
                .queuedAt(job.getQueuedAt())
                .startedAt(job.getStartedAt())
                .completedAt(job.getCompletedAt())
                .errorCode(job.getErrorCode())
                .errorMessage(job.getErrorMessage())
                .build();
    }
}
