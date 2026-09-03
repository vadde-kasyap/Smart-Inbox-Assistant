package com.clinevo.inbox.entity;

import com.fasterxml.jackson.annotation.JsonIgnore;
import jakarta.persistence.*;
import lombok.*;
import org.hibernate.annotations.CreationTimestamp;

import java.time.Instant;
import java.util.ArrayList;
import java.util.List;

@Entity
@Table(name = "EXTRACTED_FIELD")
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class ExtractedField {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @JsonIgnore
    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "ai_result_id", nullable = false)
    private AIResult aiResult;

    @Column(name = "field_group", nullable = false, length = 100)
    private String fieldGroup;

    @Column(name = "field_name", nullable = false, length = 100)
    private String fieldName;

    @Column(name = "field_value", nullable = false, length = 2000)
    private String fieldValue;

    @Column(name = "confidence", nullable = false)
    private Double confidence;

    @CreationTimestamp
    @Column(name = "created_at", nullable = false, updatable = false)
    private Instant createdAt;

    @OneToMany(mappedBy = "extractedField", cascade = CascadeType.ALL, orphanRemoval = true)
    @Builder.Default
    private List<SourceReference> sourceReferences = new ArrayList<>();

    public void addSourceReference(SourceReference ref) {
        sourceReferences.add(ref);
        ref.setExtractedField(this);
    }
}
