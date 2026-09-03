package com.clinevo.inbox.entity;

import com.fasterxml.jackson.annotation.JsonIgnore;
import jakarta.persistence.*;
import lombok.*;
import org.hibernate.annotations.CreationTimestamp;

import java.time.Instant;

@Entity
@Table(name = "SOURCE_REFERENCE")
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class SourceReference {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @JsonIgnore
    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "extracted_field_id", nullable = false)
    private ExtractedField extractedField;

    @Column(name = "source_type", nullable = false, length = 50)
    private String sourceType;

    @Column(name = "email_id")
    private Long emailId;

    @Column(name = "attachment_id")
    private Long attachmentId;

    @Column(name = "page_number")
    private Integer pageNumber;

    @Column(name = "text_snippet", length = 2000)
    private String textSnippet;

    @Column(name = "location", length = 255)
    private String location;

    @CreationTimestamp
    @Column(name = "created_at", nullable = false, updatable = false)
    private Instant createdAt;
}
