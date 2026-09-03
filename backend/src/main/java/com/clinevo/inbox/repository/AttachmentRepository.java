package com.clinevo.inbox.repository;

import com.clinevo.inbox.entity.Attachment;
import com.clinevo.inbox.entity.AttachmentStatus;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface AttachmentRepository extends JpaRepository<Attachment, Long> {
    List<Attachment> findByEmailId(Long emailId);
    Optional<Attachment> findBySha256Hash(String sha256Hash);
    List<Attachment> findByStatus(AttachmentStatus status);
}
