package com.clinevo.inbox;

import com.clinevo.inbox.client.MailboxClient;
import com.clinevo.inbox.dto.RawAttachment;
import com.clinevo.inbox.dto.RawEmail;
import com.clinevo.inbox.entity.*;
import com.clinevo.inbox.ingestion.EmailIngestionService;
import com.clinevo.inbox.queue.JobQueue;
import com.clinevo.inbox.repository.AttachmentRepository;
import com.clinevo.inbox.repository.EmailRepository;
import com.clinevo.inbox.repository.ProcessingJobRepository;
import com.clinevo.inbox.service.storage.StorageService;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.transaction.annotation.Transactional;

import java.time.Instant;
import java.util.List;
import java.util.Optional;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.when;

@SpringBootTest
@ActiveProfiles("test")
class EmailIngestionServiceTest {

    @Autowired
    private EmailIngestionService ingestionService;

    @Autowired
    private EmailRepository emailRepository;

    @Autowired
    private AttachmentRepository attachmentRepository;

    @Autowired
    private ProcessingJobRepository jobRepository;

    @MockBean
    private StorageService storageService;

    @MockBean
    private MailboxClient mailboxClient;

    @BeforeEach
    void setUp() {
        when(storageService.computeSha256(any())).thenReturn("synthetic-hash-abc-123");
        when(storageService.store(any(), any(), any())).thenReturn("/app/storage/test/file.pdf");
    }

    @Test
    @Transactional
    void shouldIngestEmailAndCreateJobsForPdfsOnly() {
        String msgId = "<test-icsr-unique-001@pharma.org>";

        RawAttachment pdfAtt = RawAttachment.builder()
                .filename("patient_report.pdf")
                .contentType("application/pdf")
                .size(1024)
                .data(new byte[]{1, 2, 3})
                .isPdf(true)
                .build();

        RawAttachment txtAtt = RawAttachment.builder()
                .filename("notes.txt")
                .contentType("text/plain")
                .size(256)
                .data(new byte[]{4, 5, 6})
                .isPdf(false)
                .build();

        RawEmail rawEmail = RawEmail.builder()
                .messageId(msgId)
                .sender("dr.smith@clinic.org")
                .subject("Adverse Event Notice")
                .body("Report details enclosed.")
                .receivedAt(Instant.now())
                .attachments(List.of(pdfAtt, txtAtt))
                .build();

        Optional<Email> result = ingestionService.ingestEmail(rawEmail);

        assertThat(result).isPresent();
        Email email = result.get();
        assertThat(email.getId()).isNotNull();
        assertThat(email.getStatus()).isEqualTo(EmailStatus.PROCESSING);

        List<Attachment> attachments = attachmentRepository.findByEmailId(email.getId());
        assertThat(attachments).hasSize(2);

        Attachment savedPdf = attachments.stream().filter(Attachment::getIsPdf).findFirst().orElseThrow();
        assertThat(savedPdf.getStatus()).isEqualTo(AttachmentStatus.QUEUED);
        assertThat(savedPdf.getProcessingJob()).isNotNull();
        assertThat(savedPdf.getProcessingJob().getStatus()).isEqualTo(JobStatus.QUEUED);

        Attachment savedTxt = attachments.stream().filter(a -> !a.getIsPdf()).findFirst().orElseThrow();
        assertThat(savedTxt.getStatus()).isEqualTo(AttachmentStatus.NOT_SUPPORTED);
        assertThat(savedTxt.getProcessingJob()).isNull();
    }

    @Test
    @Transactional
    void shouldSkipDuplicateEmailGracefully() {
        String msgId = "<test-duplicate-check@pharma.org>";

        RawEmail rawEmail = RawEmail.builder()
                .messageId(msgId)
                .sender("sender@domain.com")
                .subject("First Delivery")
                .body("First content")
                .receivedAt(Instant.now())
                .build();

        Optional<Email> firstIngest = ingestionService.ingestEmail(rawEmail);
        assertThat(firstIngest).isPresent();

        // Attempting to ingest with the same messageId
        Optional<Email> secondIngest = ingestionService.ingestEmail(rawEmail);
        assertThat(secondIngest).isEmpty();

        // Verify only 1 email with this message_id exists in repository
        Optional<Email> found = emailRepository.findByMessageId(msgId);
        assertThat(found).isPresent();
    }
}
