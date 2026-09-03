package com.clinevo.inbox.dto;

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
public class RawEmail {
    private String messageId;
    private String sender;
    private String subject;
    private Instant receivedAt;
    private String body;
    @Builder.Default
    private List<RawAttachment> attachments = new ArrayList<>();
}
