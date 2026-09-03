package com.clinevo.inbox.repository;

import com.clinevo.inbox.entity.ExtractedField;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface ExtractedFieldRepository extends JpaRepository<ExtractedField, Long> {
    List<ExtractedField> findByAiResultId(Long aiResultId);
}
