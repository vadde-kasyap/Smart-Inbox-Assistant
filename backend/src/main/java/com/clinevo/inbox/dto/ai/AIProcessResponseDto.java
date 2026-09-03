package com.clinevo.inbox.dto.ai;

import com.fasterxml.jackson.annotation.JsonAlias;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.ArrayList;
import java.util.List;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@JsonIgnoreProperties(ignoreUnknown = true)
public class AIProcessResponseDto {

    @JsonAlias({"job_id", "jobId"})
    private Long jobId;

    @JsonAlias({"model_name", "modelName"})
    private String modelName;

    @JsonAlias({"model_version", "modelVersion"})
    private String modelVersion;

    @JsonAlias({"prompt_version", "promptVersion"})
    private String promptVersion;

    private String summary;

    @Builder.Default
    private Boolean relevant = true;

    @Builder.Default
    private List<ClassificationDto> classifications = new ArrayList<>();

    @Builder.Default
    @JsonAlias({"extracted_fields", "extractedFields"})
    private List<ExtractedFieldDto> extractedFields = new ArrayList<>();

    @Builder.Default
    @JsonAlias({"image_results", "imageResults"})
    private List<ImageResultDto> imageResults = new ArrayList<>();

    private ProcessingMetricsDto metrics;

    @Builder.Default
    @JsonAlias({"validation_passed", "validationPassed"})
    private Boolean validationPassed = true;

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    @JsonIgnoreProperties(ignoreUnknown = true)
    public static class ClassificationDto {
        private String category;
        private Double confidence;
        private String reason;
    }

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    @JsonIgnoreProperties(ignoreUnknown = true)
    public static class ExtractedFieldDto {
        @JsonAlias({"field_group", "fieldGroup"})
        private String fieldGroup;

        @JsonAlias({"field_name", "fieldName"})
        private String fieldName;

        @JsonAlias({"value", "field_value", "fieldValue"})
        private String value;

        private Double confidence;

        @Builder.Default
        @JsonAlias({"source_references", "sourceReferences"})
        private List<SourceReferenceDto> sourceReferences = new ArrayList<>();
    }

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    @JsonIgnoreProperties(ignoreUnknown = true)
    public static class SourceReferenceDto {
        @JsonAlias({"source_type", "sourceType"})
        private String sourceType;

        @JsonAlias({"email_id", "emailId"})
        private Long emailId;

        @JsonAlias({"attachment_id", "attachmentId"})
        private Long attachmentId;

        @JsonAlias({"page_number", "pageNumber"})
        private Integer pageNumber;

        @JsonAlias({"text_snippet", "textSnippet"})
        private String textSnippet;

        private String location;
    }

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    @JsonIgnoreProperties(ignoreUnknown = true)
    public static class ImageResultDto {
        @JsonAlias({"page_number", "pageNumber"})
        private Integer pageNumber;

        private String description;
        private Double confidence;

        @JsonAlias({"review_required", "reviewRequired"})
        private Boolean reviewRequired;
    }

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    @JsonIgnoreProperties(ignoreUnknown = true)
    public static class ProcessingMetricsDto {
        @JsonAlias({"total_duration_ms", "totalDurationMs"})
        private Long totalDurationMs;

        @JsonAlias({"extraction_duration_ms", "extractionDurationMs"})
        private Long extractionDurationMs;

        @JsonAlias({"ocr_duration_ms", "ocrDurationMs"})
        private Long ocrDurationMs;

        @JsonAlias({"translation_duration_ms", "translationDurationMs"})
        private Long translationDurationMs;

        @JsonAlias({"llm_duration_ms", "llmDurationMs"})
        private Long llmDurationMs;

        @JsonAlias({"validation_duration_ms", "validationDurationMs"})
        private Long validationDurationMs;
    }
}
