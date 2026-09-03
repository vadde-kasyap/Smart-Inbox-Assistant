package com.clinevo.inbox.ingestion;

import lombok.Getter;
import org.springframework.context.ApplicationEvent;

import java.util.List;

@Getter
public class EmailIngestedEvent extends ApplicationEvent {

    private final Long emailId;
    private final List<Long> jobIds;

    public EmailIngestedEvent(Object source, Long emailId, List<Long> jobIds) {
        super(source);
        this.emailId = emailId;
        this.jobIds = jobIds != null ? List.copyOf(jobIds) : List.of();
    }
}
