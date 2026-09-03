package com.clinevo.inbox.dto.review;

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
public class ReviewOverrideRequest {
    private String reviewerId;
    private String justification;

    @Builder.Default
    private List<ClassificationOverrideDto> classifications = new ArrayList<>();

    @Builder.Default
    private List<FieldOverrideDto> fields = new ArrayList<>();

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class ClassificationOverrideDto {
        private String category;
        private Double confidence;
        private String reason;
    }

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class FieldOverrideDto {
        private Long fieldId;
        private String fieldGroup;
        private String fieldName;
        private String newValue;
        private Double confidence;
    }
}
