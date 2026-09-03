package com.clinevo.inbox.dto.ai;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class AIProcessRequestDto {
    private Long jobId;
    private EmailContext email;
    private DocumentContext document;

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class EmailContext {
        private Long emailId;
        private String sender;
        private String subject;
        private String body;
    }

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class DocumentContext {
        private Long attachmentId;
        private String filename;
        private String contentType;
        private String storageReference;
    }
}
