package com.clinevo.inbox.repository;

import com.clinevo.inbox.entity.Email;
import com.clinevo.inbox.entity.EmailStatus;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface EmailRepository extends JpaRepository<Email, Long> {
    Optional<Email> findByMessageId(String messageId);
    boolean existsByMessageId(String messageId);
    List<Email> findAllByOrderByReceivedAtDesc();
    List<Email> findByStatus(EmailStatus status);
}
