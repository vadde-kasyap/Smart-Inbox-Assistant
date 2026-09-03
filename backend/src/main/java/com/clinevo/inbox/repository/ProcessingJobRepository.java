package com.clinevo.inbox.repository;

import com.clinevo.inbox.entity.JobStatus;
import com.clinevo.inbox.entity.ProcessingJob;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface ProcessingJobRepository extends JpaRepository<ProcessingJob, Long> {
    Optional<ProcessingJob> findByAttachmentId(Long attachmentId);
    List<ProcessingJob> findByStatus(JobStatus status);

    @Query("SELECT j FROM ProcessingJob j WHERE j.attachment.email.id = :emailId ORDER BY j.createdAt DESC")
    List<ProcessingJob> findByEmailId(@Param("emailId") Long emailId);
}
