package com.clinevo.inbox.dto;

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
public class EmailDetailDto {
    private Long id;
    private String messageId;
    private String senderEmail;
    private String subject;
    private String body;
    private EmailStatus status;
    private Instant receivedAt;
    private Instant ingestedAt;
    @Builder.Default
    private List<AttachmentDto> attachments = new ArrayList<>();
}
