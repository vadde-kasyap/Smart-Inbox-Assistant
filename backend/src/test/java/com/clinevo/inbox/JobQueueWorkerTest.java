package com.clinevo.inbox;

import com.clinevo.inbox.entity.*;
import com.clinevo.inbox.queue.JobQueue;
import com.clinevo.inbox.queue.JobWorker;
import com.clinevo.inbox.repository.AttachmentRepository;
import com.clinevo.inbox.repository.AuditLogRepository;
import com.clinevo.inbox.repository.EmailRepository;
import com.clinevo.inbox.repository.ProcessingJobRepository;
import com.clinevo.inbox.service.JobService;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.transaction.annotation.Transactional;

import java.time.Instant;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;

@SpringBootTest
@ActiveProfiles("test")
class JobQueueWorkerTest {

    @Autowired
    private JobService jobService;

    @Autowired
    private JobQueue jobQueue;

    @Autowired
    private EmailRepository emailRepository;

    @Autowired
    private AttachmentRepository attachmentRepository;

    @Autowired
    private ProcessingJobRepository jobRepository;

    @Autowired
    private AuditLogRepository auditLogRepository;

    @org.springframework.boot.test.mock.mockito.MockBean
    private com.clinevo.inbox.client.AIClient aiClient;

    @Test
    @Transactional
    void shouldProcessJobSuccessfullyInWorker() {
        // Create test Email
        Email email = Email.builder()
                .messageId("<queue-test-" + System.currentTimeMillis() + "@test.org>")
                .senderEmail("test@test.org")
                .subject("Test Queue Subject")
                .body("Test Body")
                .receivedAt(Instant.now())
                .status(EmailStatus.PROCESSING)
                .build();
        email = emailRepository.save(email);

        // Create test Attachment
        Attachment attachment = Attachment.builder()
                .email(email)
                .filename("test_doc.pdf")
                .contentType("application/pdf")
                .fileSize(500L)
                .storageReference("/storage/test_doc.pdf")
                .sha256Hash("test-hash")
                .isPdf(true)
                .status(AttachmentStatus.QUEUED)
                .build();
        attachment = attachmentRepository.save(attachment);

        // Create ProcessingJob
        ProcessingJob job = ProcessingJob.builder()
                .attachment(attachment)
                .status(JobStatus.QUEUED)
                .retryCount(0)
                .maxRetries(3)
                .build();
        job = jobRepository.save(job);
        // Mock AIClient response
        org.mockito.Mockito.when(aiClient.process(org.mockito.ArgumentMatchers.any()))
                .thenReturn(com.clinevo.inbox.dto.ai.AIProcessResponseDto.builder()
                        .jobId(job.getId())
                        .modelName("Qwen3-VL-2B-Instruct")
                        .summary("Synthetic 10-15 sentence test summary.")
                        .validationPassed(true)
                        .classifications(java.util.List.of(
                                com.clinevo.inbox.dto.ai.AIProcessResponseDto.ClassificationDto.builder()
                                        .category("ICSR")
                                        .confidence(0.95)
                                        .reason("Adverse reaction found.")
                                        .build()
                        ))
                        .build());

        // Directly execute processJob
        jobService.processJob(job.getId());

        // Verify status transitions
        ProcessingJob updatedJob = jobRepository.findById(job.getId()).orElseThrow();
        assertThat(updatedJob.getStatus()).isEqualTo(JobStatus.COMPLETED);
        assertThat(updatedJob.getStartedAt()).isNotNull();
        assertThat(updatedJob.getCompletedAt()).isNotNull();

        Attachment updatedAttachment = attachmentRepository.findById(attachment.getId()).orElseThrow();
        assertThat(updatedAttachment.getStatus()).isEqualTo(AttachmentStatus.COMPLETED);

        // Verify audit logs
        List<AuditLog> auditLogs = auditLogRepository.findByJobIdOrderByTimestampDesc(job.getId());
        assertThat(auditLogs).isNotEmpty();
        assertThat(auditLogs.stream().anyMatch(a -> "JOB_STARTED".equals(a.getAction()))).isTrue();
        assertThat(auditLogs.stream().anyMatch(a -> "JOB_COMPLETED".equals(a.getAction()))).isTrue();
    }
}
