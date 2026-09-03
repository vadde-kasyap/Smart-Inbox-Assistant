package com.clinevo.inbox.repository;

import com.clinevo.inbox.entity.SourceReference;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface SourceReferenceRepository extends JpaRepository<SourceReference, Long> {
    List<SourceReference> findByExtractedFieldId(Long extractedFieldId);
}
