package com.clinevo.inbox.service;

import com.clinevo.inbox.entity.ActorType;
import com.clinevo.inbox.entity.AuditLog;
import com.clinevo.inbox.repository.AuditLogRepository;
import lombok.RequiredArgsConstructor;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Propagation;
import org.springframework.transaction.annotation.Transactional;

@Service
@RequiredArgsConstructor
public class AuditService {

    private static final Logger log = LoggerFactory.getLogger(AuditService.class);
    private final AuditLogRepository auditLogRepository;

    @Transactional(propagation = Propagation.REQUIRED)
    public void log(Long emailId, Long jobId, ActorType actorType, String actorId,
                    String action, String oldValue, String newValue, String metadata) {
        AuditLog auditLog = AuditLog.builder()
                .emailId(emailId)
                .jobId(jobId)
                .actorType(actorType)
                .actorId(actorId)
                .action(action)
                .oldValue(oldValue)
                .newValue(newValue)
                .metadata(metadata)
                .build();

        auditLogRepository.save(auditLog);
        log.info("AUDIT [{}] - Actor: {}:{} Email: {} Job: {} Meta: {}",
                action, actorType, actorId, emailId, jobId, metadata);
    }

    @Transactional(propagation = Propagation.REQUIRED)
    public void logSystem(Long emailId, Long jobId, String action, String metadata) {
        log(emailId, jobId, ActorType.SYSTEM, "SYSTEM", action, null, null, metadata);
    }
}
