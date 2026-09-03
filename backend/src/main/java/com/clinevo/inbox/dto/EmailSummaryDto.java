package com.clinevo.inbox.dto;

import com.clinevo.inbox.entity.EmailStatus;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.Instant;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class EmailSummaryDto {
    private Long id;
    private String messageId;
    private String senderEmail;
    private String subject;
    private EmailStatus status;
    private Instant receivedAt;
    private Instant ingestedAt;
    private int attachmentCount;
    private boolean hasPdf;
}
