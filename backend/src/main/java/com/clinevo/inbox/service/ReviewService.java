package com.clinevo.inbox.service;

import com.clinevo.inbox.dto.AttachmentDto;
import com.clinevo.inbox.dto.AuditLogDto;
import com.clinevo.inbox.dto.review.ReviewAcceptRequest;
import com.clinevo.inbox.dto.review.ReviewDetailDto;
import com.clinevo.inbox.dto.review.ReviewOverrideRequest;
import com.clinevo.inbox.dto.review.ReviewQueueItemDto;
import com.clinevo.inbox.entity.*;
import com.clinevo.inbox.exception.ResourceNotFoundException;
import com.clinevo.inbox.repository.*;
import lombok.RequiredArgsConstructor;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.ArrayList;
import java.util.List;
import java.util.Locale;

@Service
@RequiredArgsConstructor
public class ReviewService {

    private static final Logger log = LoggerFactory.getLogger(ReviewService.class);

    private final EmailRepository emailRepository;
    private final AttachmentRepository attachmentRepository;
    private final ProcessingJobRepository jobRepository;
    private final AIResultRepository aiResultRepository;
    private final ClassificationRepository classificationRepository;
    private final ExtractedFieldRepository fieldRepository;
    private final SourceReferenceRepository sourceRepository;
    private final ImageResultRepository imageRepository;
    private final ProcessingMetricsRepository metricsRepository;
    private final AuditLogRepository auditLogRepository;
    private final AuditService auditService;

    @Transactional(readOnly = true)
    public List<ReviewQueueItemDto> getReviewQueue(String categoryFilter, EmailStatus statusFilter, String search) {
        List<Email> emails = emailRepository.findAll();
        List<ReviewQueueItemDto> queueItems = new ArrayList<>();

        for (Email email : emails) {
            // Apply status filter
            if (statusFilter != null && email.getStatus() != statusFilter) {
                continue;
            }

            // Apply search filter (sender or subject)
            if (search != null && !search.isBlank()) {
                String q = search.toLowerCase(Locale.ROOT);
                boolean matchesSender = email.getSenderEmail() != null && email.getSenderEmail().toLowerCase(Locale.ROOT).contains(q);
                boolean matchesSubject = email.getSubject() != null && email.getSubject().toLowerCase(Locale.ROOT).contains(q);
                if (!matchesSender && !matchesSubject) {
                    continue;
                }
            }

            List<Attachment> attachments = attachmentRepository.findByEmailId(email.getId());
            boolean hasPdf = attachments.stream().anyMatch(a -> Boolean.TRUE.equals(a.getIsPdf()));

            // Find AI results for this email
            List<AIResult> results = aiResultRepository.findByEmailId(email.getId());
            AIResult latestResult = results.isEmpty() ? null : results.get(results.size() - 1);

            List<String> categories = new ArrayList<>();
            String primaryCat = "UNCLASSIFIED";
            Double primaryConf = 0.0;
            String summaryPreview = null;

            if (latestResult != null) {
                List<Classification> classifications = classificationRepository.findByAiResultId(latestResult.getId());
                for (Classification c : classifications) {
                    categories.add(c.getCategory());
                    if (c.getConfidence() > primaryConf) {
                        primaryConf = c.getConfidence();
                        primaryCat = c.getCategory();
                    }
                }
                if (latestResult.getSummary() != null) {
                    summaryPreview = latestResult.getSummary().length() > 180
                            ? latestResult.getSummary().substring(0, 180) + "..."
                            : latestResult.getSummary();
                }
            }

            List<ProcessingJob> jobs = jobRepository.findByEmailId(email.getId());
            ProcessingJob latestJob = jobs.isEmpty() ? null : jobs.get(0);
            String jobStatus = latestJob != null ? latestJob.getStatus().name() : (email.getStatus() == EmailStatus.RECEIVED ? "QUEUED" : "NONE");
            int progressPercent = 100;
            String progressMessage = "AI analysis complete";
            boolean inQueue = false;

            if (latestJob != null) {
                switch (latestJob.getStatus()) {
                    case QUEUED:
                        progressPercent = 25;
                        progressMessage = "Waiting in queue";
                        inQueue = true;
                        break;
                    case PROCESSING:
                        progressPercent = 65;
                        progressMessage = "AI analyzing text & extracting facts...";
                        inQueue = true;
                        break;
                    case RETRYING:
                        progressPercent = 40;
                        progressMessage = "Retrying analysis...";
                        inQueue = true;
                        break;
                    case FAILED:
                        progressPercent = 100;
                        progressMessage = "AI processing failed";
                        inQueue = false;
                        break;
                    case COMPLETED:
                    default:
                        progressPercent = 100;
                        progressMessage = "AI analysis complete";
                        inQueue = false;
                        break;
                }
            } else if (email.getStatus() == EmailStatus.RECEIVED || email.getStatus() == EmailStatus.PROCESSING) {
                progressPercent = 20;
                progressMessage = "In queue • Awaiting AI worker";
                inQueue = true;
            }

            // Apply category filter
            if (categoryFilter != null && !categoryFilter.isBlank() && !categoryFilter.equalsIgnoreCase("ALL")) {
                if (categoryFilter.equalsIgnoreCase("QUEUED") || categoryFilter.equalsIgnoreCase("IN_QUEUE")) {
                    if (!inQueue && email.getStatus() != EmailStatus.RECEIVED && email.getStatus() != EmailStatus.PROCESSING) {
                        continue;
                    }
                } else if (!categories.contains(categoryFilter.toUpperCase(Locale.ROOT))) {
                    continue;
                }
            }

            queueItems.add(ReviewQueueItemDto.builder()
                    .emailId(email.getId())
                    .sender(email.getSenderEmail())
                    .subject(email.getSubject())
                    .receivedAt(email.getReceivedAt())
                    .status(email.getStatus())
                    .hasPdf(hasPdf)
                    .attachmentCount(attachments.size())
                    .primaryCategory(primaryCat)
                    .primaryConfidence(primaryConf)
                    .categories(categories)
                    .summaryPreview(summaryPreview)
                    .jobStatus(jobStatus)
                    .progressPercent(progressPercent)
                    .progressMessage(progressMessage)
                    .inQueue(inQueue)
                    .build());
        }

        // Sort: newest first
        queueItems.sort((a, b) -> b.getReceivedAt().compareTo(a.getReceivedAt()));
        return queueItems;
    }

    @Transactional(readOnly = true)
    public ReviewDetailDto getReviewDetail(Long emailId) {
        Email email = emailRepository.findById(emailId)
                .orElseThrow(() -> new ResourceNotFoundException("Email not found with id: " + emailId));

        List<Attachment> attachments = attachmentRepository.findByEmailId(emailId);
        List<AttachmentDto> attachmentDtos = attachments.stream()
                .map(a -> AttachmentDto.builder()
                        .id(a.getId())
                        .filename(a.getFilename())
                        .contentType(a.getContentType())
                        .fileSize(a.getFileSize())
                        .isPdf(a.getIsPdf())
                        .status(a.getStatus())
                        .build())
                .toList();

        // Latest AI Result
        List<AIResult> results = aiResultRepository.findByEmailId(emailId);
        ReviewDetailDto.AIResultDetail aiDetail = null;

        if (!results.isEmpty()) {
            AIResult latestResult = results.get(results.size() - 1);
            List<Classification> classifications = classificationRepository.findByAiResultId(latestResult.getId());
            List<ExtractedField> fields = fieldRepository.findByAiResultId(latestResult.getId());
            List<ImageResult> images = imageRepository.findByAiResultId(latestResult.getId());
            ProcessingMetrics metrics = metricsRepository.findLatestByJobId(latestResult.getJobId()).orElse(null);

            List<ReviewDetailDto.ClassificationItem> classItems = classifications.stream()
                    .map(c -> ReviewDetailDto.ClassificationItem.builder()
                            .id(c.getId())
                            .category(c.getCategory())
                            .confidence(c.getConfidence())
                            .reason(c.getReason())
                            .build())
                    .toList();

            List<ReviewDetailDto.ExtractedFieldItem> fieldItems = fields.stream()
                    .map(f -> {
                        List<SourceReference> sources = sourceRepository.findByExtractedFieldId(f.getId());
                        List<ReviewDetailDto.SourceReferenceItem> srcItems = sources.stream()
                                .map(s -> ReviewDetailDto.SourceReferenceItem.builder()
                                        .id(s.getId())
                                        .sourceType(s.getSourceType())
                                        .emailId(s.getEmailId())
                                        .attachmentId(s.getAttachmentId())
                                        .pageNumber(s.getPageNumber())
                                        .textSnippet(s.getTextSnippet())
                                        .location(s.getLocation())
                                        .build())
                                .toList();

                        return ReviewDetailDto.ExtractedFieldItem.builder()
                                .id(f.getId())
                                .fieldGroup(f.getFieldGroup())
                                .fieldName(f.getFieldName())
                                .value(f.getFieldValue())
                                .confidence(f.getConfidence())
                                .sourceReferences(srcItems)
                                .build();
                    })
                    .toList();

            List<ReviewDetailDto.ImageResultItem> imgItems = images.stream()
                    .map(i -> ReviewDetailDto.ImageResultItem.builder()
                            .id(i.getId())
                            .pageNumber(i.getPageNumber())
                            .description(i.getDescription())
                            .confidence(i.getConfidence())
                            .reviewRequired(i.getReviewRequired())
                            .build())
                    .toList();

            ReviewDetailDto.MetricsItem metricsItem = null;
            if (metrics != null) {
                metricsItem = ReviewDetailDto.MetricsItem.builder()
                        .totalDurationMs(metrics.getTotalDurationMs())
                        .extractionDurationMs(metrics.getExtractionDurationMs())
                        .ocrDurationMs(metrics.getOcrDurationMs())
                        .translationDurationMs(metrics.getTranslationDurationMs())
                        .llmDurationMs(metrics.getLlmDurationMs())
                        .validationDurationMs(metrics.getValidationDurationMs())
                        .build();
            }

            aiDetail = ReviewDetailDto.AIResultDetail.builder()
                    .id(latestResult.getId())
                    .jobId(latestResult.getJobId())
                    .modelName(latestResult.getModelName())
                    .modelVersion(latestResult.getModelVersion())
                    .summary(latestResult.getSummary())
                    .relevant(latestResult.getRelevant())
                    .classifications(classItems)
                    .extractedFields(fieldItems)
                    .imageResults(imgItems)
                    .metrics(metricsItem)
                    .build();
        }

        // Audit Trail
        List<AuditLog> auditLogs = auditLogRepository.findByEmailIdOrderByTimestampDesc(emailId);
        List<AuditLogDto> auditHistory = auditLogs.stream()
                .map(l -> AuditLogDto.builder()
                        .id(l.getId())
                        .emailId(l.getEmailId())
                        .jobId(l.getJobId())
                        .actorType(l.getActorType())
                        .actorId(l.getActorId())
                        .action(l.getAction())
                        .oldValue(l.getOldValue())
                        .newValue(l.getNewValue())
                        .metadata(l.getMetadata())
                        .timestamp(l.getTimestamp())
                        .build())
                .toList();

        List<ProcessingJob> detailJobs = jobRepository.findByEmailId(emailId);
        ProcessingJob detailLatestJob = detailJobs.isEmpty() ? null : detailJobs.get(0);
        String detailJobStatus = detailLatestJob != null ? detailLatestJob.getStatus().name() : (email.getStatus() == EmailStatus.RECEIVED ? "QUEUED" : "NONE");
        int detailProgressPercent = 100;
        String detailProgressMessage = "AI analysis complete";
        boolean detailInQueue = false;

        if (detailLatestJob != null) {
            switch (detailLatestJob.getStatus()) {
                case QUEUED:
                    detailProgressPercent = 25;
                    detailProgressMessage = "Waiting in queue for AI processing";
                    detailInQueue = true;
                    break;
                case PROCESSING:
                    detailProgressPercent = 65;
                    detailProgressMessage = "AI analyzing text & extracting clinical facts...";
                    detailInQueue = true;
                    break;
                case RETRYING:
                    detailProgressPercent = 40;
                    detailProgressMessage = "Retrying analysis...";
                    detailInQueue = true;
                    break;
                case FAILED:
                    detailProgressPercent = 100;
                    detailProgressMessage = "AI processing failed";
                    detailInQueue = false;
                    break;
                case COMPLETED:
                default:
                    detailProgressPercent = 100;
                    detailProgressMessage = "AI analysis complete";
                    detailInQueue = false;
                    break;
            }
        } else if (email.getStatus() == EmailStatus.RECEIVED || email.getStatus() == EmailStatus.PROCESSING) {
            detailProgressPercent = 20;
            detailProgressMessage = "In queue • Awaiting AI worker";
            detailInQueue = true;
        }

        return ReviewDetailDto.builder()
                .emailId(email.getId())
                .sender(email.getSenderEmail())
                .subject(email.getSubject())
                .body(email.getBody())
                .receivedAt(email.getReceivedAt())
                .status(email.getStatus())
                .jobStatus(detailJobStatus)
                .progressPercent(detailProgressPercent)
                .progressMessage(detailProgressMessage)
                .inQueue(detailInQueue)
                .attachments(attachmentDtos)
                .aiResult(aiDetail)
                .auditHistory(auditHistory)
                .build();
    }

    @Transactional
    public ReviewDetailDto acceptReview(Long emailId, ReviewAcceptRequest request) {
        Email email = emailRepository.findById(emailId)
                .orElseThrow(() -> new ResourceNotFoundException("Email not found with id: " + emailId));

        email.setStatus(EmailStatus.REVIEWED);
        emailRepository.save(email);

        String reviewer = (request != null && request.getReviewerId() != null) ? request.getReviewerId() : "reviewer-1";
        String notes = (request != null && request.getComments() != null) ? request.getComments() : "AI recommendations accepted by reviewer.";

        auditService.log(emailId, null, ActorType.REVIEWER, reviewer, "REVIEW_ACCEPTED", null, null,
                String.format("{\"notes\":\"%s\"}", notes));

        log.info("Review ACCEPTED for Email ID: {} by {}", emailId, reviewer);
        return getReviewDetail(emailId);
    }

    @Transactional
    public ReviewDetailDto overrideReview(Long emailId, ReviewOverrideRequest request) {
        Email email = emailRepository.findById(emailId)
                .orElseThrow(() -> new ResourceNotFoundException("Email not found with id: " + emailId));

        String reviewer = (request != null && request.getReviewerId() != null) ? request.getReviewerId() : "reviewer-1";
        String reason = (request != null && request.getJustification() != null) ? request.getJustification() : "Reviewer override applied.";

        // 1. Process Field Overrides
        if (request != null && request.getFields() != null) {
            for (ReviewOverrideRequest.FieldOverrideDto fOverride : request.getFields()) {
                if (fOverride.getFieldId() != null) {
                    ExtractedField field = fieldRepository.findById(fOverride.getFieldId()).orElse(null);
                    if (field != null) {
                        String oldVal = field.getFieldValue();
                        field.setFieldValue(fOverride.getNewValue());
                        if (fOverride.getConfidence() != null) {
                            field.setConfidence(fOverride.getConfidence());
                        }
                        fieldRepository.save(field);

                        auditService.log(emailId, null, ActorType.REVIEWER, reviewer, "REVIEW_OVERRIDE",
                                String.format("%s.%s = %s", field.getFieldGroup(), field.getFieldName(), oldVal),
                                String.format("%s.%s = %s", field.getFieldGroup(), field.getFieldName(), fOverride.getNewValue()),
                                String.format("{\"fieldId\":%d,\"reason\":\"%s\"}", field.getId(), reason));
                    }
                }
            }
        }

        // 2. Process Classification Overrides
        if (request != null && request.getClassifications() != null && !request.getClassifications().isEmpty()) {
            List<AIResult> results = aiResultRepository.findByEmailId(emailId);
            if (!results.isEmpty()) {
                AIResult latest = results.get(results.size() - 1);
                // Replace classifications
                List<Classification> currentClassifications = classificationRepository.findByAiResultId(latest.getId());
                String oldClasses = currentClassifications.stream().map(Classification::getCategory).toList().toString();

                classificationRepository.deleteAll(currentClassifications);

                List<String> newCategories = new ArrayList<>();
                for (ReviewOverrideRequest.ClassificationOverrideDto cDto : request.getClassifications()) {
                    Classification c = Classification.builder()
                            .aiResult(latest)
                            .category(cDto.getCategory())
                            .confidence(cDto.getConfidence() != null ? cDto.getConfidence() : 1.0)
                            .reason(cDto.getReason() != null ? cDto.getReason() : reason)
                            .build();
                    classificationRepository.save(c);
                    newCategories.add(c.getCategory());
                }

                auditService.log(emailId, null, ActorType.REVIEWER, reviewer, "REVIEW_OVERRIDE",
                        oldClasses, newCategories.toString(),
                        String.format("{\"reason\":\"%s\"}", reason));
            }
        }

        email.setStatus(EmailStatus.REVIEWED);
        emailRepository.save(email);

        log.info("Review OVERRIDDEN for Email ID: {} by {}", emailId, reviewer);
        return getReviewDetail(emailId);
    }
}
