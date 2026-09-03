package com.clinevo.inbox.entity;

import jakarta.persistence.*;
import lombok.*;
import org.hibernate.annotations.CreationTimestamp;

import java.time.Instant;
import java.util.ArrayList;
import java.util.List;

@Entity
@Table(name = "AI_RESULT")
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class AIResult {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "job_id", nullable = false)
    private Long jobId;

    @Column(name = "email_id", nullable = false)
    private Long emailId;

    @Column(name = "model_name", nullable = false, length = 100)
    private String modelName;

    @Column(name = "model_version", length = 50)
    private String modelVersion;

    @Column(name = "prompt_version", length = 50)
    private String promptVersion;

    @Lob
    @Column(name = "summary")
    private String summary;

    @Column(name = "relevant", nullable = false)
    @Builder.Default
    private Boolean relevant = true;

    @CreationTimestamp
    @Column(name = "created_at", nullable = false, updatable = false)
    private Instant createdAt;

    @OneToMany(mappedBy = "aiResult", cascade = CascadeType.ALL, orphanRemoval = true)
    @Builder.Default
    private List<Classification> classifications = new ArrayList<>();

    @OneToMany(mappedBy = "aiResult", cascade = CascadeType.ALL, orphanRemoval = true)
    @Builder.Default
    private List<ExtractedField> extractedFields = new ArrayList<>();

    @OneToMany(mappedBy = "aiResult", cascade = CascadeType.ALL, orphanRemoval = true)
    @Builder.Default
    private List<ImageResult> imageResults = new ArrayList<>();

    public void addClassification(Classification c) {
        classifications.add(c);
        c.setAiResult(this);
    }

    public void addExtractedField(ExtractedField f) {
        extractedFields.add(f);
        f.setAiResult(this);
    }

    public void addImageResult(ImageResult img) {
        imageResults.add(img);
        img.setAiResult(this);
    }
}
