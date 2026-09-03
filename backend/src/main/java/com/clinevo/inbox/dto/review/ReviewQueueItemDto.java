package com.clinevo.inbox.dto.review;

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
public class ReviewQueueItemDto {
    private Long emailId;
    private String sender;
    private String subject;
    private Instant receivedAt;
    private EmailStatus status;
    private Boolean hasPdf;
    private Integer attachmentCount;
    private String primaryCategory;
    private Double primaryConfidence;
    @Builder.Default
    private List<String> categories = new ArrayList<>();
    private String summaryPreview;

    // AI Progress and Queue Status Tracking
    private String jobStatus;
    private Integer progressPercent;
    private String progressMessage;
    private Boolean inQueue;
}
