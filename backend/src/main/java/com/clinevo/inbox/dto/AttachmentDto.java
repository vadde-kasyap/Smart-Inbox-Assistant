package com.clinevo.inbox.dto;

import com.clinevo.inbox.entity.AttachmentStatus;
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
public class AttachmentDto {
    private Long id;
    private Long emailId;
    private String filename;
    private String contentType;
    private Long fileSize;
    private String storageReference;
    private String sha256Hash;
    private Boolean isPdf;
    private AttachmentStatus status;
    private Instant createdAt;
    private Long jobId;
    private JobStatus jobStatus;
}
