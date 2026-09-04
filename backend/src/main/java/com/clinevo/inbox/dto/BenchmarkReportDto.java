package com.clinevo.inbox.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * One row in the batch benchmark report (AGENTS.md §18).
 * Reports: filename, document type, classification, processing time, success/failure.
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class BenchmarkReportDto {
    private Long jobId;
    private String filename;
    private String documentType;
    private String classification;
    private long processingTimeMs;
    private boolean success;
    private String status;
    private String errorMessage;
}
