package com.clinevo.inbox.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class RawAttachment {
    private String filename;
    private String contentType;
    private long size;
    private byte[] data;
    private String sha256;
    private boolean isPdf;
}
