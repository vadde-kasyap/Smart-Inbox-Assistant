package com.clinevo.inbox.service;

import com.clinevo.inbox.dto.ai.AIProcessResponseDto;
import com.clinevo.inbox.entity.*;
import com.clinevo.inbox.exception.ResourceNotFoundException;
import com.clinevo.inbox.repository.*;
import lombok.RequiredArgsConstructor;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.Instant;
import java.util.List;

@Service
@RequiredArgsConstructor
public class ResultService {

    private static final Logger log = LoggerFactory.getLogger(ResultService.class);

    private final ProcessingJobRepository jobRepository;
    private final AttachmentRepository attachmentRepository;
    private final EmailRepository emailRepository;
    private final AIResultRepository aiResultRepository;
    private final ProcessingMetricsRepository metricsRepository;
    private final AuditService auditService;

    @Transactional
    public AIResult persistResult(Long jobId, AIProcessResponseDto response) {
        ProcessingJob job = jobRepository.findById(jobId)
                .orElseThrow(() -> new ResourceNotFoundException("Job not found with id: " + jobId));

        Attachment attachment = job.getAttachment();
        Email email = attachment != null ? attachment.getEmail() : null;
        Long emailId = email != null ? email.getId() : null;

        // 1. Create and Save AI_RESULT
        AIResult aiResult = AIResult.builder()
                .jobId(jobId)
                .emailId(emailId != null ? emailId : 0L)
                .modelName(response.getModelName() != null ? response.getModelName() : "Qwen3-VL-2B-Instruct")
                .modelVersion(response.getModelVersion() != null ? response.getModelVersion() : "v1.0")
                .promptVersion(response.getPromptVersion() != null ? response.getPromptVersion() : "v1")
                .summary(response.getSummary())
                .relevant(response.getRelevant() != null ? response.getRelevant() : true)
                .build();

        // 2. Classifications
        if (response.getClassifications() != null) {
            for (AIProcessResponseDto.ClassificationDto cDto : response.getClassifications()) {
                Classification c = Classification.builder()
                        .category(cDto.getCategory())
                        .confidence(cDto.getConfidence())
                        .reason(cDto.getReason())
                        .build();
                aiResult.addClassification(c);
            }
        }

        // 3. Extracted Fields and Source References
        if (response.getExtractedFields() != null) {
            for (AIProcessResponseDto.ExtractedFieldDto fDto : response.getExtractedFields()) {
                ExtractedField field = ExtractedField.builder()
                        .fieldGroup(fDto.getFieldGroup())
                        .fieldName(fDto.getFieldName())
                        .fieldValue(fDto.getValue())
                        .confidence(fDto.getConfidence())
                        .build();

                if (fDto.getSourceReferences() != null) {
                    for (AIProcessResponseDto.SourceReferenceDto sDto : fDto.getSourceReferences()) {
                        SourceReference source = SourceReference.builder()
                                .sourceType(sDto.getSourceType() != null ? sDto.getSourceType() : "PDF")
                                .emailId(emailId)
                                .attachmentId(attachment != null ? attachment.getId() : null)
                                .pageNumber(sDto.getPageNumber())
                                .textSnippet(sDto.getTextSnippet())
                                .location(sDto.getLocation())
                                .build();
                        field.addSourceReference(source);
                    }
                }
                aiResult.addExtractedField(field);
            }
        }

        // 4. Image Results
        if (response.getImageResults() != null) {
            for (AIProcessResponseDto.ImageResultDto imgDto : response.getImageResults()) {
                ImageResult img = ImageResult.builder()
                        .attachmentId(attachment != null ? attachment.getId() : 0L)
                        .pageNumber(imgDto.getPageNumber())
                        .description(imgDto.getDescription())
                        .confidence(imgDto.getConfidence())
                        .reviewRequired(imgDto.getReviewRequired() != null ? imgDto.getReviewRequired() : true)
                        .build();
                aiResult.addImageResult(img);
            }
        }

        aiResult = aiResultRepository.save(aiResult);
        log.info("Persisted AIResult ID: {} for Job ID: {}", aiResult.getId(), jobId);

        // 5. Processing Metrics
        if (response.getMetrics() != null) {
            AIProcessResponseDto.ProcessingMetricsDto mDto = response.getMetrics();
            ProcessingMetrics metrics = ProcessingMetrics.builder()
                    .jobId(jobId)
                    .totalDurationMs(mDto.getTotalDurationMs())
                    .extractionDurationMs(mDto.getExtractionDurationMs())
                    .ocrDurationMs(mDto.getOcrDurationMs())
                    .translationDurationMs(mDto.getTranslationDurationMs())
                    .llmDurationMs(mDto.getLlmDurationMs())
                    .validationDurationMs(mDto.getValidationDurationMs())
                    .build();
            metricsRepository.save(metrics);
        }

        // 6. Update Job State: PROCESSING -> COMPLETED
        job.setStatus(JobStatus.COMPLETED);
        job.setCompletedAt(Instant.now());
        job.setErrorCode(null);
        job.setErrorMessage(null);
        jobRepository.save(job);

        // 7. Update Attachment State: PROCESSING -> COMPLETED
        if (attachment != null) {
            attachment.setStatus(AttachmentStatus.COMPLETED);
            attachmentRepository.save(attachment);
        }

        // 8. Update Email State -> REVIEW_REQUIRED
        if (email != null) {
            email.setStatus(EmailStatus.REVIEW_REQUIRED);
            emailRepository.save(email);
        }

        // 9. Audit Entries
        auditService.log(emailId, jobId, ActorType.AI, response.getModelName(),
                "AI_COMPLETED", null, null,
                String.format("{\"aiResultId\":%d,\"classifications\":%d,\"fields\":%d}",
                        aiResult.getId(), aiResult.getClassifications().size(), aiResult.getExtractedFields().size()));

        for (Classification c : aiResult.getClassifications()) {
            auditService.log(emailId, jobId, ActorType.AI, response.getModelName(),
                    "CLASSIFICATION_CREATED", null, c.getCategory(),
                    String.format("{\"category\":\"%s\",\"confidence\":%.2f}", c.getCategory(), c.getConfidence()));
        }

        return aiResult;
    }
}
