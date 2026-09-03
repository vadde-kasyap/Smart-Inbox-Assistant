package com.clinevo.inbox.repository;

import com.clinevo.inbox.entity.ImageResult;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface ImageResultRepository extends JpaRepository<ImageResult, Long> {
    List<ImageResult> findByAiResultId(Long aiResultId);
}
