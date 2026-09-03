package com.clinevo.inbox.entity;

import jakarta.persistence.*;
import lombok.*;
import org.hibernate.annotations.CreationTimestamp;

import java.time.Instant;

@Entity
@Table(name = "PROCESSING_METRICS")
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class ProcessingMetrics {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "job_id", nullable = false)
    private Long jobId;

    @Column(name = "total_duration_ms")
    private Long totalDurationMs;

    @Column(name = "extraction_duration_ms")
    private Long extractionDurationMs;

    @Column(name = "ocr_duration_ms")
    private Long ocrDurationMs;

    @Column(name = "translation_duration_ms")
    private Long translationDurationMs;

    @Column(name = "llm_duration_ms")
    private Long llmDurationMs;

    @Column(name = "validation_duration_ms")
    private Long validationDurationMs;

    @CreationTimestamp
    @Column(name = "created_at", nullable = false, updatable = false)
    private Instant createdAt;
}
