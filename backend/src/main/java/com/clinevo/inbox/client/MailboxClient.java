package com.clinevo.inbox.client;

import com.clinevo.inbox.dto.RawEmail;

import java.util.List;

public interface MailboxClient {
    List<RawEmail> fetchNewMessages();
    void markProcessed(String messageId);
}
