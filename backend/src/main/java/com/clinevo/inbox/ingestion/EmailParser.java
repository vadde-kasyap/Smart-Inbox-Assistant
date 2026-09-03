package com.clinevo.inbox.ingestion;

import com.clinevo.inbox.dto.RawAttachment;
import com.clinevo.inbox.dto.RawEmail;
import com.clinevo.inbox.service.storage.StorageService;
import jakarta.mail.Address;
import jakarta.mail.BodyPart;
import jakarta.mail.MessagingException;
import jakarta.mail.Part;
import jakarta.mail.internet.MimeMessage;
import jakarta.mail.internet.MimeMultipart;
import lombok.RequiredArgsConstructor;
import org.apache.commons.io.IOUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;

import java.io.ByteArrayInputStream;
import java.io.IOException;
import java.io.InputStream;
import java.time.Instant;
import java.util.ArrayList;
import java.util.Date;
import java.util.List;
import java.util.UUID;

@Component
@RequiredArgsConstructor
public class EmailParser {

    private static final Logger log = LoggerFactory.getLogger(EmailParser.class);
    private final StorageService storageService;

    public RawEmail parse(MimeMessage message) throws MessagingException, IOException {
        String messageId = message.getMessageID();
        if (messageId == null || messageId.isBlank()) {
            messageId = "<gen-" + UUID.randomUUID() + "@clinevo.local>";
        }

        String sender = "unknown@unknown.com";
        Address[] fromAddresses = message.getFrom();
        if (fromAddresses != null && fromAddresses.length > 0) {
            sender = fromAddresses[0].toString();
        }

        String subject = message.getSubject() != null ? message.getSubject() : "No Subject";

        Date sentDate = message.getSentDate();
        Instant receivedAt = sentDate != null ? sentDate.toInstant() : Instant.now();

        StringBuilder bodyBuilder = new StringBuilder();
        List<RawAttachment> attachments = new ArrayList<>();

        extractParts(message, bodyBuilder, attachments);

        String body = bodyBuilder.toString().trim();
        if (body.isEmpty()) {
            body = "No body text";
        }

        return RawEmail.builder()
                .messageId(messageId)
                .sender(sender)
                .subject(subject)
                .receivedAt(receivedAt)
                .body(body)
                .attachments(attachments)
                .build();
    }

    public RawEmail parse(byte[] emlBytes) throws MessagingException, IOException {
        jakarta.mail.Session session = jakarta.mail.Session.getDefaultInstance(new java.util.Properties());
        MimeMessage message = new MimeMessage(session, new ByteArrayInputStream(emlBytes));
        return parse(message);
    }

    private void extractParts(Part part, StringBuilder bodyBuilder, List<RawAttachment> attachments)
            throws MessagingException, IOException {

        String disposition = part.getDisposition();
        String contentType = part.getContentType().toLowerCase();
        String filename = part.getFileName();

        boolean isAttachment = Part.ATTACHMENT.equalsIgnoreCase(disposition) ||
                (filename != null && !filename.isBlank());

        if (isAttachment) {
            byte[] data;
            try (InputStream is = (part.getDataHandler() != null) ? part.getDataHandler().getInputStream() : part.getInputStream()) {
                data = IOUtils.toByteArray(is);
            }
            String safeFilename = (filename != null && !filename.isBlank()) ? filename : "attachment_" + (attachments.size() + 1);
            boolean isPdf = safeFilename.toLowerCase().endsWith(".pdf") || contentType.contains("application/pdf");
            String sha256 = storageService.computeSha256(data);

            attachments.add(RawAttachment.builder()
                    .filename(safeFilename)
                    .contentType(part.getContentType())
                    .size(data.length)
                    .data(data)
                    .sha256(sha256)
                    .isPdf(isPdf)
                    .build());
            return;
        }

        if (part.isMimeType("text/plain")) {
            Object content = part.getContent();
            if (content instanceof String s) {
                bodyBuilder.append(s).append("\n");
            } else if (content instanceof InputStream is) {
                bodyBuilder.append(IOUtils.toString(is, java.nio.charset.StandardCharsets.UTF_8)).append("\n");
            }
        } else if (part.isMimeType("text/html")) {
            // Prefer plain text if already present, otherwise add html
            if (bodyBuilder.isEmpty()) {
                Object content = part.getContent();
                if (content instanceof String s) {
                    bodyBuilder.append(s).append("\n");
                } else if (content instanceof InputStream is) {
                    bodyBuilder.append(IOUtils.toString(is, java.nio.charset.StandardCharsets.UTF_8)).append("\n");
                }
            }
        } else if (part.isMimeType("multipart/*")) {
            MimeMultipart multipart = (MimeMultipart) part.getContent();
            for (int i = 0; i < multipart.getCount(); i++) {
                BodyPart bodyPart = multipart.getBodyPart(i);
                extractParts(bodyPart, bodyBuilder, attachments);
            }
        } else {
            // Non-text part without explicit disposition: treat as attachment if it has bytes
            try (InputStream is = (part.getDataHandler() != null) ? part.getDataHandler().getInputStream() : part.getInputStream()) {
                byte[] data = IOUtils.toByteArray(is);
                if (data.length > 0) {
                    String safeFilename = (filename != null && !filename.isBlank()) ? filename : "part_" + (attachments.size() + 1);
                    boolean isPdf = safeFilename.toLowerCase().endsWith(".pdf") || contentType.contains("application/pdf");
                    String sha256 = storageService.computeSha256(data);
                    attachments.add(RawAttachment.builder()
                            .filename(safeFilename)
                            .contentType(part.getContentType())
                            .size(data.length)
                            .data(data)
                            .sha256(sha256)
                            .isPdf(isPdf)
                            .build());
                }
            }
        }
    }
}
