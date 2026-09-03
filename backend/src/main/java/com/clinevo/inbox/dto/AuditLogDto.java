package com.clinevo.inbox.dto;

import com.clinevo.inbox.entity.ActorType;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.Instant;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class AuditLogDto {
    private Long id;
    private Long emailId;
    private Long jobId;
    private ActorType actorType;
    private String actorId;
    private String action;
    private String oldValue;
    private String newValue;
    private String metadata;
    private Instant timestamp;
}
