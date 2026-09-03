package com.clinevo.inbox.service;

import com.clinevo.inbox.dto.AttachmentDto;
import com.clinevo.inbox.dto.EmailDetailDto;
import com.clinevo.inbox.dto.EmailSummaryDto;
import com.clinevo.inbox.entity.Attachment;
import com.clinevo.inbox.entity.Email;
import com.clinevo.inbox.exception.ResourceNotFoundException;
import com.clinevo.inbox.repository.AttachmentRepository;
import com.clinevo.inbox.repository.EmailRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;

@Service
@RequiredArgsConstructor
@Transactional(readOnly = true)
public class EmailService {

    private final EmailRepository emailRepository;
    private final AttachmentRepository attachmentRepository;
    private final com.clinevo.inbox.service.storage.StorageService storageService;

    public List<EmailSummaryDto> getAllEmails() {
        return emailRepository.findAllByOrderByReceivedAtDesc().stream()
                .map(this::toSummaryDto)
                .toList();
    }

    public EmailDetailDto getEmailById(Long emailId) {
        Email email = emailRepository.findById(emailId)
                .orElseThrow(() -> new ResourceNotFoundException("Email not found with id: " + emailId));

        List<AttachmentDto> attachmentDtos = attachmentRepository.findByEmailId(emailId).stream()
                .map(this::toAttachmentDto)
                .toList();

        return EmailDetailDto.builder()
                .id(email.getId())
                .messageId(email.getMessageId())
                .senderEmail(email.getSenderEmail())
                .subject(email.getSubject())
                .body(email.getBody())
                .status(email.getStatus())
                .receivedAt(email.getReceivedAt())
                .ingestedAt(email.getIngestedAt())
                .attachments(attachmentDtos)
                .build();
    }

    public List<AttachmentDto> getAttachmentsByEmailId(Long emailId) {
        if (!emailRepository.existsById(emailId)) {
            throw new ResourceNotFoundException("Email not found with id: " + emailId);
        }
        return attachmentRepository.findByEmailId(emailId).stream()
                .map(this::toAttachmentDto)
                .toList();
    }

    private EmailSummaryDto toSummaryDto(Email email) {
        List<Attachment> attachments = attachmentRepository.findByEmailId(email.getId());
        boolean hasPdf = attachments.stream().anyMatch(a -> Boolean.TRUE.equals(a.getIsPdf()));

        return EmailSummaryDto.builder()
                .id(email.getId())
                .messageId(email.getMessageId())
                .senderEmail(email.getSenderEmail())
                .subject(email.getSubject())
                .status(email.getStatus())
                .receivedAt(email.getReceivedAt())
                .ingestedAt(email.getIngestedAt())
                .attachmentCount(attachments.size())
                .hasPdf(hasPdf)
                .build();
    }

    private AttachmentDto toAttachmentDto(Attachment att) {
        Long jobId = null;
        com.clinevo.inbox.entity.JobStatus jobStatus = null;
        if (att.getProcessingJob() != null) {
            jobId = att.getProcessingJob().getId();
            jobStatus = att.getProcessingJob().getStatus();
        }

        return AttachmentDto.builder()
                .id(att.getId())
                .emailId(att.getEmail().getId())
                .filename(att.getFilename())
                .contentType(att.getContentType())
                .fileSize(att.getFileSize())
                .storageReference(att.getStorageReference())
                .sha256Hash(att.getSha256Hash())
                .isPdf(att.getIsPdf())
                .status(att.getStatus())
                .createdAt(att.getCreatedAt())
                .jobId(jobId)
                .jobStatus(jobStatus)
                .build();
    }

    public Attachment getAttachment(Long emailId, Long attachmentId) {
        Attachment attachment = attachmentRepository.findById(attachmentId)
                .orElseThrow(() -> new ResourceNotFoundException("Attachment not found with id: " + attachmentId));
        if (!attachment.getEmail().getId().equals(emailId)) {
            throw new ResourceNotFoundException("Attachment does not belong to email id: " + emailId);
        }
        return attachment;
    }

    public byte[] getAttachmentContent(Long emailId, Long attachmentId) {
        Attachment attachment = getAttachment(emailId, attachmentId);
        try {
            return storageService.load(attachment.getStorageReference());
        } catch (Exception e) {
            throw new RuntimeException("Failed to read attachment file: " + e.getMessage(), e);
        }
    }
}
