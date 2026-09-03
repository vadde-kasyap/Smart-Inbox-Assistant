package com.clinevo.inbox.dto;

import com.clinevo.inbox.entity.JobStatus;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.Instant;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class JobDto {
    private Long id;
    private Long attachmentId;
    private Long emailId;
    private String filename;
    private JobStatus status;
    private Integer retryCount;
    private Integer maxRetries;
    private Instant queuedAt;
    private Instant startedAt;
    private Instant completedAt;
    private String errorCode;
    private String errorMessage;
}
