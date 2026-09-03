package com.clinevo.inbox;

import com.clinevo.inbox.dto.ai.AIProcessResponseDto;
import com.clinevo.inbox.dto.review.ReviewAcceptRequest;
import com.clinevo.inbox.dto.review.ReviewDetailDto;
import com.clinevo.inbox.dto.review.ReviewOverrideRequest;
import com.clinevo.inbox.dto.review.ReviewQueueItemDto;
import com.clinevo.inbox.entity.Attachment;
import com.clinevo.inbox.entity.AttachmentStatus;
import com.clinevo.inbox.entity.Email;
import com.clinevo.inbox.entity.EmailStatus;
import com.clinevo.inbox.entity.ProcessingJob;
import com.clinevo.inbox.entity.JobStatus;
import com.clinevo.inbox.repository.AttachmentRepository;
import com.clinevo.inbox.repository.EmailRepository;
import com.clinevo.inbox.repository.ProcessingJobRepository;
import com.clinevo.inbox.service.ResultService;
import com.clinevo.inbox.service.ReviewService;
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
class ReviewServiceTest {

    @Autowired
    private ReviewService reviewService;

    @Autowired
    private ResultService resultService;

    @Autowired
    private EmailRepository emailRepository;

    @Autowired
    private AttachmentRepository attachmentRepository;

    @Autowired
    private ProcessingJobRepository jobRepository;

    @Test
    @Transactional
    void shouldGetQueueAndDetailAndPerformAcceptAndOverride() {
        // 1. Setup email with attachment and job
        Email email = emailRepository.save(Email.builder()
                .messageId("<review-test-" + System.currentTimeMillis() + "@test.org>")
                .senderEmail("reporter@clinic.org")
                .subject("Adverse Rash Case")
                .body("Patient 45F developed rash.")
                .receivedAt(Instant.now())
                .status(EmailStatus.REVIEW_REQUIRED)
                .build());

        Attachment attachment = attachmentRepository.save(Attachment.builder()
                .email(email)
                .filename("rash_report.pdf")
                .contentType("application/pdf")
                .fileSize(2048L)
                .storageReference("/storage/rash_report.pdf")
                .sha256Hash("hash-abc")
                .isPdf(true)
                .status(AttachmentStatus.PROCESSING)
                .build());

        ProcessingJob job = jobRepository.save(ProcessingJob.builder()
                .attachment(attachment)
                .status(JobStatus.PROCESSING)
                .retryCount(0)
                .maxRetries(3)
                .build());

        // 2. Persist AI Result
        resultService.persistResult(job.getId(), AIProcessResponseDto.builder()
                .jobId(job.getId())
                .modelName("Qwen3-VL-2B-Instruct")
                .summary("Patient 45F experienced rash after drug ingestion. Classified as ICSR.")
                .relevant(true)
                .classifications(List.of(
                        AIProcessResponseDto.ClassificationDto.builder()
                                .category("ICSR")
                                .confidence(0.94)
                                .reason("Adverse reaction documented.")
                                .build()
                ))
                .extractedFields(List.of(
                        AIProcessResponseDto.ExtractedFieldDto.builder()
                                .fieldGroup("patient")
                                .fieldName("age")
                                .value("45")
                                .confidence(0.92)
                                .sourceReferences(List.of(
                                        AIProcessResponseDto.SourceReferenceDto.builder()
                                                .sourceType("PDF")
                                                .pageNumber(1)
                                                .textSnippet("Patient age: 45")
                                                .location("pdf-page")
                                                .build()
                                ))
                                .build()
                ))
                .build());

        // 3. Test Queue retrieval
        List<ReviewQueueItemDto> queue = reviewService.getReviewQueue(null, null, "reporter@clinic.org");
        assertThat(queue).isNotEmpty();
        ReviewQueueItemDto item = queue.get(0);
        assertThat(item.getEmailId()).isEqualTo(email.getId());
        assertThat(item.getPrimaryCategory()).isEqualTo("ICSR");

        // 4. Test Detail retrieval
        ReviewDetailDto detail = reviewService.getReviewDetail(email.getId());
        assertThat(detail).isNotNull();
        assertThat(detail.getAiResult()).isNotNull();
        assertThat(detail.getAiResult().getClassifications()).hasSize(1);
        assertThat(detail.getAiResult().getExtractedFields()).hasSize(1);
        Long fieldId = detail.getAiResult().getExtractedFields().get(0).getId();

        // 5. Test Accept
        ReviewDetailDto accepted = reviewService.acceptReview(email.getId(),
                ReviewAcceptRequest.builder().reviewerId("rev-01").comments("Confirmed.").build());
        assertThat(accepted.getStatus()).isEqualTo(EmailStatus.REVIEWED);

        // 6. Test Override
        ReviewDetailDto overridden = reviewService.overrideReview(email.getId(),
                ReviewOverrideRequest.builder()
                        .reviewerId("rev-02")
                        .justification("Patient corrected to 46")
                        .fields(List.of(
                                ReviewOverrideRequest.FieldOverrideDto.builder()
                                        .fieldId(fieldId)
                                        .fieldGroup("patient")
                                        .fieldName("age")
                                        .newValue("46")
                                        .confidence(1.0)
                                        .build()
                        ))
                        .build());

        assertThat(overridden.getStatus()).isEqualTo(EmailStatus.REVIEWED);
        ReviewDetailDto.ExtractedFieldItem updatedField = overridden.getAiResult().getExtractedFields().stream()
                .filter(f -> f.getId().equals(fieldId))
                .findFirst().orElseThrow();
        assertThat(updatedField.getValue()).isEqualTo("46");

        // Verify audit log has the override
        assertThat(overridden.getAuditHistory()).anyMatch(a ->
                "REVIEW_OVERRIDE".equals(a.getAction()) && a.getOldValue().contains("45") && a.getNewValue().contains("46")
        );
    }
}
