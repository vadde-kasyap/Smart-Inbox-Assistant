package com.clinevo.inbox.client;

import com.clinevo.inbox.dto.RawEmail;
import com.clinevo.inbox.ingestion.EmailParser;
import jakarta.mail.*;
import jakarta.mail.internet.MimeMessage;
import jakarta.mail.search.FlagTerm;
import lombok.RequiredArgsConstructor;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.stereotype.Component;

import java.util.ArrayList;
import java.util.List;
import java.util.Properties;

@Component
@ConditionalOnProperty(name = "mailbox.type", havingValue = "imap")
@RequiredArgsConstructor
public class ImapMailboxClient implements MailboxClient {

    private static final Logger log = LoggerFactory.getLogger(ImapMailboxClient.class);
    private final EmailParser emailParser;

    @Value("${mailbox.imap.host:imap.example.com}")
    private String host;

    @Value("${mailbox.imap.port:993}")
    private int port;

    @Value("${mailbox.imap.username:}")
    private String username;

    @Value("${mailbox.imap.password:}")
    private String password;

    @Value("${mailbox.imap.folder:INBOX}")
    private String folderName;

    @Value("${mailbox.imap.ssl:true}")
    private boolean ssl;

    @Override
    public List<RawEmail> fetchNewMessages() {
        List<RawEmail> emails = new ArrayList<>();

        if (username == null || username.isBlank() || password == null || password.isBlank()) {
            log.warn("IMAP credentials not configured. Skipping fetch.");
            return emails;
        }

        Properties properties = new Properties();
        String protocol = ssl ? "imaps" : "imap";
        properties.put(String.format("mail.%s.host", protocol), host);
        properties.put(String.format("mail.%s.port", protocol), String.valueOf(port));
        properties.put(String.format("mail.%s.ssl.enable", protocol), String.valueOf(ssl));
        properties.put(String.format("mail.%s.connectiontimeout", protocol), "10000");
        properties.put(String.format("mail.%s.timeout", protocol), "10000");

        Session session = Session.getInstance(properties);
        Store store = null;
        Folder folder = null;

        try {
            store = session.getStore(protocol);
            store.connect(host, port, username, password);

            folder = store.getFolder(folderName);
            folder.open(Folder.READ_WRITE);

            // Fetch unread messages
            Message[] messages = folder.search(new FlagTerm(new Flags(Flags.Flag.SEEN), false));
            log.info("IMAP check on {}:{}/{} found {} unread messages", host, port, folderName, messages.length);

            for (Message msg : messages) {
                if (msg instanceof MimeMessage mimeMessage) {
                    try {
                        RawEmail rawEmail = emailParser.parse(mimeMessage);
                        emails.add(rawEmail);
                    } catch (Exception e) {
                        log.error("Failed parsing message {}: {}", msg.getMessageNumber(), e.getMessage(), e);
                    }
                }
            }
        } catch (MessagingException e) {
            log.error("IMAP connection failed to {}:{} - {}", host, port, e.getMessage());
        } finally {
            try {
                if (folder != null && folder.isOpen()) {
                    folder.close(false);
                }
                if (store != null && store.isConnected()) {
                    store.close();
                }
            } catch (Exception e) {
                log.warn("Error closing IMAP resources: {}", e.getMessage());
            }
        }

        return emails;
    }

    @Override
    public void markProcessed(String messageId) {
        log.info("Marking IMAP message {} as processed", messageId);
    }
}
