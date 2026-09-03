package com.clinevo.inbox;

import com.clinevo.inbox.dto.ai.AIProcessResponseDto;
import com.clinevo.inbox.entity.*;
import com.clinevo.inbox.repository.*;
import com.clinevo.inbox.service.ResultService;
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
class ResultServiceTest {

    @Autowired
    private ResultService resultService;

    @Autowired
    private EmailRepository emailRepository;

    @Autowired
    private AttachmentRepository attachmentRepository;

    @Autowired
    private ProcessingJobRepository jobRepository;

    @Autowired
    private AIResultRepository aiResultRepository;

    @Autowired
    private ClassificationRepository classificationRepository;

    @Autowired
    private ExtractedFieldRepository fieldRepository;

    @Autowired
    private ProcessingMetricsRepository metricsRepository;

    @Test
    @Transactional
    void shouldPersistAIResultGraphAtomically() {
        // Given
        Email email = emailRepository.save(Email.builder()
                .messageId("<result-test-" + System.currentTimeMillis() + "@test.org>")
                .senderEmail("safety@test.org")
                .subject("Adverse Event Notice")
                .body("Patient 54M developed rash.")
                .receivedAt(Instant.now())
                .status(EmailStatus.PROCESSING)
                .build());

        Attachment attachment = attachmentRepository.save(Attachment.builder()
                .email(email)
                .filename("report.pdf")
                .contentType("application/pdf")
                .fileSize(1024L)
                .storageReference("/storage/report.pdf")
                .sha256Hash("hash-12345")
                .isPdf(true)
                .status(AttachmentStatus.PROCESSING)
                .build());

        ProcessingJob job = jobRepository.save(ProcessingJob.builder()
                .attachment(attachment)
                .status(JobStatus.PROCESSING)
                .retryCount(0)
                .maxRetries(3)
                .build());

        AIProcessResponseDto response = AIProcessResponseDto.builder()
                .jobId(job.getId())
                .modelName("Qwen3-VL-2B-Instruct")
                .modelVersion("v1.0")
                .promptVersion("v1")
                .summary("Patient 54M experienced an adverse rash after taking SynthoStatin. Report is classified as ICSR.")
                .relevant(true)
                .classifications(List.of(
                        AIProcessResponseDto.ClassificationDto.builder()
                                .category("ICSR")
                                .confidence(0.96)
                                .reason("Adverse reaction documented.")
                                .build(),
                        AIProcessResponseDto.ClassificationDto.builder()
                                .category("PQC")
                                .confidence(0.85)
                                .reason("Particulate matter observed.")
                                .build()
                ))
                .extractedFields(List.of(
                        AIProcessResponseDto.ExtractedFieldDto.builder()
                                .fieldGroup("patient")
                                .fieldName("age")
                                .value("54")
                                .confidence(0.95)
                                .sourceReferences(List.of(
                                        AIProcessResponseDto.SourceReferenceDto.builder()
                                                .sourceType("PDF")
                                                .pageNumber(1)
                                                .textSnippet("Patient age: 54 years")
                                                .location("pdf-page")
                                                .build()
                                ))
                                .build(),
                        AIProcessResponseDto.ExtractedFieldDto.builder()
                                .fieldGroup("product")
                                .fieldName("name")
                                .value("SynthoStatin")
                                .confidence(0.98)
                                .sourceReferences(List.of(
                                        AIProcessResponseDto.SourceReferenceDto.builder()
                                                .sourceType("PDF")
                                                .pageNumber(1)
                                                .textSnippet("Prescribed: SynthoStatin 20mg")
                                                .location("pdf-page")
                                                .build()
                                ))
                                .build()
                ))
                .metrics(AIProcessResponseDto.ProcessingMetricsDto.builder()
                        .totalDurationMs(250L)
                        .extractionDurationMs(50L)
                        .llmDurationMs(180L)
                        .validationDurationMs(20L)
                        .build())
                .validationPassed(true)
                .build();

        // When
        AIResult persisted = resultService.persistResult(job.getId(), response);

        // Then
        assertThat(persisted).isNotNull();
        assertThat(persisted.getId()).isNotNull();
        assertThat(persisted.getModelName()).isEqualTo("Qwen3-VL-2B-Instruct");
        assertThat(persisted.getSummary()).contains("SynthoStatin");

        // Verify Classifications
        List<Classification> classifications = classificationRepository.findByAiResultId(persisted.getId());
        assertThat(classifications).hasSize(2);
        assertThat(classifications).extracting(Classification::getCategory).containsExactlyInAnyOrder("ICSR", "PQC");

        // Verify Extracted Fields
        List<ExtractedField> fields = fieldRepository.findByAiResultId(persisted.getId());
        assertThat(fields).hasSize(2);
        ExtractedField ageField = fields.stream().filter(f -> f.getFieldName().equals("age")).findFirst().orElseThrow();
        assertThat(ageField.getFieldValue()).isEqualTo("54");
        assertThat(ageField.getSourceReferences()).hasSize(1);
        assertThat(ageField.getSourceReferences().get(0).getPageNumber()).isEqualTo(1);

        // Verify Processing Metrics
        ProcessingMetrics metrics = metricsRepository.findLatestByJobId(job.getId()).orElseThrow();
        assertThat(metrics.getTotalDurationMs()).isEqualTo(250L);

        // Verify Job & Email Status transitions
        ProcessingJob updatedJob = jobRepository.findById(job.getId()).orElseThrow();
        assertThat(updatedJob.getStatus()).isEqualTo(JobStatus.COMPLETED);

        Email updatedEmail = emailRepository.findById(email.getId()).orElseThrow();
        assertThat(updatedEmail.getStatus()).isEqualTo(EmailStatus.REVIEW_REQUIRED);
    }
}
