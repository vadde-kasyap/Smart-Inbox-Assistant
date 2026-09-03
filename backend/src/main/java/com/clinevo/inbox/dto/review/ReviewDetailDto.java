package com.clinevo.inbox.dto.review;

import com.clinevo.inbox.dto.AttachmentDto;
import com.clinevo.inbox.dto.AuditLogDto;
import com.clinevo.inbox.dto.ai.AIProcessResponseDto;
import com.clinevo.inbox.entity.EmailStatus;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.Instant;
import java.util.ArrayList;
import java.util.List;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ReviewDetailDto {
    private Long emailId;
    private String sender;
    private String subject;
    private String body;
    private Instant receivedAt;
    private EmailStatus status;
    private String jobStatus;
    private Integer progressPercent;
    private String progressMessage;
    private Boolean inQueue;

    @Builder.Default
    private List<AttachmentDto> attachments = new ArrayList<>();

    private AIResultDetail aiResult;

    @Builder.Default
    private List<AuditLogDto> auditHistory = new ArrayList<>();

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class AIResultDetail {
        private Long id;
        private Long jobId;
        private String modelName;
        private String modelVersion;
        private String summary;
        private Boolean relevant;
        @Builder.Default
        private List<ClassificationItem> classifications = new ArrayList<>();
        @Builder.Default
        private List<ExtractedFieldItem> extractedFields = new ArrayList<>();
        @Builder.Default
        private List<ImageResultItem> imageResults = new ArrayList<>();
        private MetricsItem metrics;
    }

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class ClassificationItem {
        private Long id;
        private String category;
        private Double confidence;
        private String reason;
    }

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class ExtractedFieldItem {
        private Long id;
        private String fieldGroup;
        private String fieldName;
        private String value;
        private Double confidence;
        @Builder.Default
        private List<SourceReferenceItem> sourceReferences = new ArrayList<>();
    }

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class SourceReferenceItem {
        private Long id;
        private String sourceType;
        private Long emailId;
        private Long attachmentId;
        private Integer pageNumber;
        private String textSnippet;
        private String location;
    }

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class ImageResultItem {
        private Long id;
        private Integer pageNumber;
        private String description;
        private Double confidence;
        private Boolean reviewRequired;
    }

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class MetricsItem {
        private Long totalDurationMs;
        private Long extractionDurationMs;
        private Long ocrDurationMs;
        private Long translationDurationMs;
        private Long llmDurationMs;
        private Long validationDurationMs;
    }
}
