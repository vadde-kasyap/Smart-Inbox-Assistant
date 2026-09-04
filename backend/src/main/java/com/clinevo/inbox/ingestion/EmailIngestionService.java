package com.clinevo.inbox.ingestion;

import com.clinevo.inbox.client.MailboxClient;
import com.clinevo.inbox.dto.RawAttachment;
import com.clinevo.inbox.dto.RawEmail;
import com.clinevo.inbox.entity.*;
import com.clinevo.inbox.queue.JobQueue;
import com.clinevo.inbox.repository.AttachmentRepository;
import com.clinevo.inbox.repository.EmailRepository;
import com.clinevo.inbox.repository.ProcessingJobRepository;
import com.clinevo.inbox.service.AuditService;
import com.clinevo.inbox.service.storage.StorageService;
import jakarta.annotation.PostConstruct;
import lombok.RequiredArgsConstructor;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.ApplicationEventPublisher;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.transaction.event.TransactionPhase;
import org.springframework.transaction.event.TransactionalEventListener;

import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;
import java.util.Optional;

@Service
@RequiredArgsConstructor
public class EmailIngestionService {

    private static final Logger log = LoggerFactory.getLogger(EmailIngestionService.class);

    private final MailboxClient mailboxClient;
    private final EmailRepository emailRepository;
    private final AttachmentRepository attachmentRepository;
    private final ProcessingJobRepository jobRepository;
    private final StorageService storageService;
    private final AuditService auditService;
    private final JobQueue jobQueue;
    private final ApplicationEventPublisher eventPublisher;

    @Value("${inbox.worker.max-retries:3}")
    private int maxRetries;

    /**
     * Poll mailbox and ingest new emails periodically or on-demand.
     */
    @Scheduled(fixedDelayString = "${inbox.poll.interval-ms:60000}")
    public int pollAndIngest() {
        log.info("Starting mailbox poll cycle...");
        List<RawEmail> rawEmails = mailboxClient.fetchNewMessages();
        int ingestedCount = 0;

        for (RawEmail rawEmail : rawEmails) {
            try {
                Optional<Email> ingested = ingestEmail(rawEmail);
                if (ingested.isPresent()) {
                    ingestedCount++;
                }
            } catch (Exception e) {
                log.error("Failed to ingest email with messageId: {}: {}",
                        rawEmail.getMessageId(), e.getMessage(), e);
            }
        }

        log.info("Completed mailbox ingestion cycle. {} new emails ingested.", ingestedCount);
        return ingestedCount;
    }

    /**
     * Process all existing unanalyzed emails on startup so none remain stuck.
     */
    @PostConstruct
    @Transactional
    public void processPendingReceivedEmails() {
        List<Email> receivedEmails = emailRepository.findByStatus(EmailStatus.RECEIVED);
        for (Email email : receivedEmails) {
            List<ProcessingJob> existingJobs = jobRepository.findByEmailId(email.getId());
            if (existingJobs.isEmpty()) {
                byte[] bodyBytes = (email.getBody() != null ? email.getBody().getBytes(StandardCharsets.UTF_8) : new byte[0]);
                String sha256 = storageService.computeSha256(bodyBytes);
                String storageRef = storageService.store(email.getId(), "email_body.txt", bodyBytes);

                Attachment bodyAtt = Attachment.builder()
                        .email(email)
                        .filename("email_body.txt")
                        .contentType("text/plain")
                        .fileSize((long) bodyBytes.length)
                        .storageReference(storageRef)
                        .sha256Hash(sha256)
                        .isPdf(false)
                        .status(AttachmentStatus.QUEUED)
                        .build();

                bodyAtt = attachmentRepository.save(bodyAtt);

                ProcessingJob job = ProcessingJob.builder()
                        .attachment(bodyAtt)
                        .status(JobStatus.QUEUED)
                        .retryCount(0)
                        .maxRetries(maxRetries)
                        .build();

                job = jobRepository.save(job);
                bodyAtt.setProcessingJob(job);

                email.setStatus(EmailStatus.PROCESSING);
                emailRepository.save(email);

                jobQueue.enqueue(job.getId());
                log.info("Queued existing unanalyzed Email ID: {} as Job ID: {}", email.getId(), job.getId());
            }
        }
    }

    @Transactional
    public Optional<Email> ingestEmail(RawEmail rawEmail) {
        String messageId = rawEmail.getMessageId();

        // 1. Idempotency Check: EMAIL.message_id
        if (emailRepository.existsByMessageId(messageId)) {
            log.info("Idempotency: Email with message_id {} already exists. Skipping.", messageId);
            auditService.logSystem(null, null, "EMAIL_DUPLICATE_SKIPPED",
                    String.format("{\"messageId\":\"%s\"}", messageId));
            return Optional.empty();
        }

        // 2. Persist Email Entity
        Email email = Email.builder()
                .messageId(messageId)
                .senderEmail(rawEmail.getSender())
                .subject(rawEmail.getSubject())
                .body(rawEmail.getBody())
                .receivedAt(rawEmail.getReceivedAt())
                .status(EmailStatus.RECEIVED)
                .build();

        email = emailRepository.save(email);
        final Long emailId = email.getId();
        log.info("Persisted new Email ID: {}, message_id: {}", emailId, messageId);

        auditService.logSystem(emailId, null, "EMAIL_RECEIVED",
                String.format("{\"sender\":\"%s\",\"subject\":\"%s\"}",
                        rawEmail.getSender(), rawEmail.getSubject()));

        List<Long> newlyCreatedJobIds = new ArrayList<>();

        // 3. Process Attachments
        if (rawEmail.getAttachments() != null) {
            for (RawAttachment rawAtt : rawEmail.getAttachments()) {
                String sha256 = rawAtt.getSha256();
                if (sha256 == null && rawAtt.getData() != null) {
                    sha256 = storageService.computeSha256(rawAtt.getData());
                }

                // Store file content
                String storageRef = null;
                if (rawAtt.getData() != null && rawAtt.getData().length > 0) {
                    storageRef = storageService.store(emailId, rawAtt.getFilename(), rawAtt.getData());
                }

                Attachment attachment = Attachment.builder()
                        .email(email)
                        .filename(rawAtt.getFilename())
                        .contentType(rawAtt.getContentType())
                        .fileSize(rawAtt.getSize())
                        .storageReference(storageRef)
                        .sha256Hash(sha256)
                        .isPdf(rawAtt.isPdf())
                        .status(rawAtt.isPdf() ? AttachmentStatus.QUEUED : AttachmentStatus.NOT_SUPPORTED)
                        .build();

                attachment = attachmentRepository.save(attachment);

                if (rawAtt.isPdf()) {
                    ProcessingJob job = ProcessingJob.builder()
                            .attachment(attachment)
                            .status(JobStatus.QUEUED)
                            .retryCount(0)
                            .maxRetries(maxRetries)
                            .build();

                    job = jobRepository.save(job);
                    attachment.setProcessingJob(job);
                    newlyCreatedJobIds.add(job.getId());

                    auditService.logSystem(emailId, job.getId(), "JOB_QUEUED",
                            String.format("{\"attachmentId\":%d,\"filename\":\"%s\"}",
                                    attachment.getId(), attachment.getFilename()));

                    log.info("Created ProcessingJob ID: {} for PDF Attachment ID: {} ({})",
                            job.getId(), attachment.getId(), attachment.getFilename());
                } else {
                    log.info("Non-PDF attachment ID: {} ({}) saved",
                            attachment.getId(), attachment.getFilename());
                }

                email.addAttachment(attachment);
            }
        }

        // If email has NO PDF attachments, create a virtual text attachment for the email body so the AI analyzes it!
        if (newlyCreatedJobIds.isEmpty()) {
            byte[] bodyBytes = (rawEmail.getBody() != null ? rawEmail.getBody().getBytes(StandardCharsets.UTF_8) : new byte[0]);
            String sha256 = storageService.computeSha256(bodyBytes);
            String storageRef = storageService.store(emailId, "email_body.txt", bodyBytes);

            Attachment bodyAttachment = Attachment.builder()
                    .email(email)
                    .filename("email_body.txt")
                    .contentType("text/plain")
                    .fileSize((long) bodyBytes.length)
                    .storageReference(storageRef)
                    .sha256Hash(sha256)
                    .isPdf(false)
                    .status(AttachmentStatus.QUEUED)
                    .build();

            bodyAttachment = attachmentRepository.save(bodyAttachment);

            ProcessingJob job = ProcessingJob.builder()
                    .attachment(bodyAttachment)
                    .status(JobStatus.QUEUED)
                    .retryCount(0)
                    .maxRetries(maxRetries)
                    .build();

            job = jobRepository.save(job);
            bodyAttachment.setProcessingJob(job);
            newlyCreatedJobIds.add(job.getId());

            auditService.logSystem(emailId, job.getId(), "JOB_QUEUED",
                    String.format("{\"attachmentId\":%d,\"filename\":\"%s\"}",
                            bodyAttachment.getId(), bodyAttachment.getFilename()));

            log.info("Created ProcessingJob ID: {} for Email Body Text Attachment ID: {}",
                    job.getId(), bodyAttachment.getId());

            email.addAttachment(bodyAttachment);
        }

        // 4. Update Email status if it has processing jobs
        if (!newlyCreatedJobIds.isEmpty()) {
            email.setStatus(EmailStatus.PROCESSING);
            emailRepository.save(email);
        }

        // 5. Fire post-commit event for enqueueing
        eventPublisher.publishEvent(new EmailIngestedEvent(this, emailId, newlyCreatedJobIds));

        return Optional.of(email);
    }

    /**
     * Non-negotiable rule 12: "Only enqueue work after the database transaction successfully commits."
     */
    @TransactionalEventListener(phase = TransactionPhase.AFTER_COMMIT, fallbackExecution = true)
    public void onEmailIngested(EmailIngestedEvent event) {
        log.info("Transaction committed for Email ID: {}. Enqueueing {} job(s)...",
                event.emailId(), event.jobIds().size());

        for (Long jobId : event.jobIds()) {
            jobQueue.enqueue(jobId);
        }
    }

    public record EmailIngestedEvent(Object source, Long emailId, List<Long> jobIds) {}
}
