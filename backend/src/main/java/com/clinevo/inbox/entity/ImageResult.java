package com.clinevo.inbox.entity;

import com.fasterxml.jackson.annotation.JsonIgnore;
import jakarta.persistence.*;
import lombok.*;
import org.hibernate.annotations.CreationTimestamp;

import java.time.Instant;

@Entity
@Table(name = "IMAGE_RESULT")
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class ImageResult {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @JsonIgnore
    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "ai_result_id", nullable = false)
    private AIResult aiResult;

    @Column(name = "attachment_id", nullable = false)
    private Long attachmentId;

    @Column(name = "page_number", nullable = false)
    private Integer pageNumber;

    @Column(name = "description", length = 2000)
    private String description;

    @Column(name = "confidence")
    private Double confidence;

    @Column(name = "review_required", nullable = false)
    @Builder.Default
    private Boolean reviewRequired = true;

    @CreationTimestamp
    @Column(name = "created_at", nullable = false, updatable = false)
    private Instant createdAt;
}
