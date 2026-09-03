package com.clinevo.inbox.entity;

import jakarta.persistence.*;
import lombok.*;
import org.hibernate.annotations.CreationTimestamp;

import java.time.Instant;

@Entity
@Table(name = "AUDIT_LOG")
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class AuditLog {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "email_id")
    private Long emailId;

    @Column(name = "job_id")
    private Long jobId;

    @Enumerated(EnumType.STRING)
    @Column(name = "actor_type", nullable = false, length = 50)
    private ActorType actorType;

    @Column(name = "actor_id", length = 100)
    private String actorId;

    @Column(name = "action", nullable = false, length = 100)
    private String action;

    @Lob
    @Column(name = "old_value")
    private String oldValue;

    @Lob
    @Column(name = "new_value")
    private String newValue;

    @Lob
    @Column(name = "metadata")
    private String metadata;

    @CreationTimestamp
    @Column(name = "timestamp", nullable = false, updatable = false)
    private Instant timestamp;
}
