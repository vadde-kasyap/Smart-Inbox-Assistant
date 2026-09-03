package com.clinevo.inbox.controller;

import com.clinevo.inbox.dto.*;
import com.clinevo.inbox.entity.Email;
import com.clinevo.inbox.ingestion.EmailIngestionService;
import com.clinevo.inbox.service.EmailService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import java.time.Instant;
import java.util.*;

@RestController
@RequestMapping("/api/emails")
@RequiredArgsConstructor
@CrossOrigin(origins = "*")
public class EmailController {

    private final EmailService emailService;
    private final EmailIngestionService ingestionService;

    @GetMapping
    public ResponseEntity<ApiResponse<List<EmailSummaryDto>>> getAllEmails() {
        List<EmailSummaryDto> list = emailService.getAllEmails();
        return ResponseEntity.ok(ApiResponse.ok(list));
    }

    @GetMapping("/{id}")
    public ResponseEntity<ApiResponse<EmailDetailDto>> getEmailById(@PathVariable Long id) {
        EmailDetailDto detail = emailService.getEmailById(id);
        return ResponseEntity.ok(ApiResponse.ok(detail));
    }

    @GetMapping("/{id}/attachments")
    public ResponseEntity<ApiResponse<List<AttachmentDto>>> getEmailAttachments(@PathVariable Long id) {
        List<AttachmentDto> attachments = emailService.getAttachmentsByEmailId(id);
        return ResponseEntity.ok(ApiResponse.ok(attachments));
    }

    @GetMapping("/{emailId}/attachments/{attachmentId}/content")
    public ResponseEntity<byte[]> getAttachmentContent(
            @PathVariable Long emailId,
            @PathVariable Long attachmentId) {
        com.clinevo.inbox.entity.Attachment att = emailService.getAttachment(emailId, attachmentId);
        byte[] data = emailService.getAttachmentContent(emailId, attachmentId);
        String contentType = att.getContentType() != null ? att.getContentType() : "application/octet-stream";

        return ResponseEntity.ok()
                .header(HttpHeaders.CONTENT_DISPOSITION, "inline; filename=\"" + att.getFilename() + "\"")
                .contentType(MediaType.parseMediaType(contentType))
                .body(data);
    }

    @PostMapping("/poll")
    public ResponseEntity<ApiResponse<Map<String, Object>>> triggerPoll() {
        int count = ingestionService.pollAndIngest();
        return ResponseEntity.ok(ApiResponse.ok("Mailbox poll executed successfully",
                Map.of("newlyIngestedCount", count)));
    }

    @PostMapping(value = "/upload", consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    public ResponseEntity<ApiResponse<EmailDetailDto>> uploadEmail(
            @RequestParam("sender") String sender,
            @RequestParam("subject") String subject,
            @RequestParam(value = "body", required = false) String body,
            @RequestParam(value = "file", required = false) MultipartFile file) throws Exception {

        List<RawAttachment> attachments = new ArrayList<>();
        if (file != null && !file.isEmpty()) {
            String filename = file.getOriginalFilename() != null ? file.getOriginalFilename() : "document.pdf";
            String contentType = file.getContentType() != null ? file.getContentType() : "application/pdf";
            boolean isPdf = filename.toLowerCase().endsWith(".pdf") || contentType.toLowerCase().contains("pdf");

            attachments.add(RawAttachment.builder()
                    .filename(filename)
                    .contentType(contentType)
                    .data(file.getBytes())
                    .size(file.getSize())
                    .isPdf(isPdf)
                    .build());
        }

        RawEmail rawEmail = RawEmail.builder()
                .messageId("<manual-" + UUID.randomUUID() + "@clinevo.local>")
                .sender(sender != null && !sender.isBlank() ? sender : "manual-entry@clinevo.local")
                .subject(subject != null && !subject.isBlank() ? subject : "Manual Case Report")
                .body(body != null ? body : "")
                .receivedAt(Instant.now())
                .attachments(attachments)
                .build();

        Optional<Email> ingested = ingestionService.ingestEmail(rawEmail);
        if (ingested.isEmpty()) {
            return ResponseEntity.badRequest().body(ApiResponse.error("Failed to ingest email or duplicate detected"));
        }

        EmailDetailDto detail = emailService.getEmailById(ingested.get().getId());
        return ResponseEntity.ok(ApiResponse.ok("Email and attachment successfully ingested", detail));
    }
}
