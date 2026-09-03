package com.clinevo.inbox.entity;

import jakarta.persistence.*;
import lombok.*;
import org.hibernate.annotations.CreationTimestamp;

import java.time.Instant;

@Entity
@Table(name = "ATTACHMENT")
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class Attachment {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.EAGER)
    @JoinColumn(name = "email_id", nullable = false)
    private Email email;

    @Column(name = "filename", nullable = false, length = 255)
    private String filename;

    @Column(name = "content_type", length = 100)
    private String contentType;

    @Column(name = "file_size")
    private Long fileSize;

    @Column(name = "storage_reference", length = 500)
    private String storageReference;

    @Column(name = "sha256_hash", length = 64)
    private String sha256Hash;

    @Column(name = "is_pdf", nullable = false)
    @Builder.Default
    private Boolean isPdf = false;

    @Enumerated(EnumType.STRING)
    @Column(name = "status", nullable = false, length = 50)
    @Builder.Default
    private AttachmentStatus status = AttachmentStatus.RECEIVED;

    @CreationTimestamp
    @Column(name = "created_at", nullable = false, updatable = false)
    private Instant createdAt;

    @OneToOne(mappedBy = "attachment", cascade = CascadeType.ALL, orphanRemoval = true, fetch = FetchType.LAZY)
    private ProcessingJob processingJob;

    public void setProcessingJob(ProcessingJob processingJob) {
        this.processingJob = processingJob;
        if (processingJob != null) {
            processingJob.setAttachment(this);
        }
    }
}
