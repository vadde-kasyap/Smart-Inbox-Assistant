package com.clinevo.inbox.repository;

import com.clinevo.inbox.entity.ProcessingMetrics;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface ProcessingMetricsRepository extends JpaRepository<ProcessingMetrics, Long> {
    List<ProcessingMetrics> findByJobIdOrderByCreatedAtDesc(Long jobId);

    default Optional<ProcessingMetrics> findLatestByJobId(Long jobId) {
        List<ProcessingMetrics> list = findByJobIdOrderByCreatedAtDesc(jobId);
        return list.isEmpty() ? Optional.empty() : Optional.of(list.get(0));
    }
}
