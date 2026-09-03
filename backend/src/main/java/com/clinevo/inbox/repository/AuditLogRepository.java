package com.clinevo.inbox.repository;

import com.clinevo.inbox.entity.AuditLog;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface AuditLogRepository extends JpaRepository<AuditLog, Long> {
    List<AuditLog> findByEmailIdOrderByTimestampDesc(Long emailId);
    List<AuditLog> findByJobIdOrderByTimestampDesc(Long jobId);
}
