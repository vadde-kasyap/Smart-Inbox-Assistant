package com.clinevo.inbox.repository;

import com.clinevo.inbox.entity.AIResult;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface AIResultRepository extends JpaRepository<AIResult, Long> {
    Optional<AIResult> findByJobId(Long jobId);
    List<AIResult> findByEmailId(Long emailId);
}
