package com.clinevo.inbox.entity;

public enum JobStatus {
    QUEUED,
    PROCESSING,
    RETRYING,
    COMPLETED,
    REVIEW_REQUIRED,
    FAILED
}
