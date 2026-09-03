package com.clinevo.inbox.repository;

import com.clinevo.inbox.entity.Classification;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface ClassificationRepository extends JpaRepository<Classification, Long> {
    List<Classification> findByAiResultId(Long aiResultId);
}
