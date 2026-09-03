package com.clinevo.inbox.client;

import com.clinevo.inbox.dto.RawEmail;
import com.clinevo.inbox.ingestion.EmailParser;
import lombok.RequiredArgsConstructor;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.stereotype.Component;

import java.io.File;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.stream.Stream;

@Component
@ConditionalOnProperty(name = "mailbox.type", havingValue = "mock", matchIfMissing = true)
@RequiredArgsConstructor
public class MockMailboxClient implements MailboxClient {

    private static final Logger log = LoggerFactory.getLogger(MockMailboxClient.class);
    private final EmailParser emailParser;

    @Value("${mailbox.mock.path:./test-data/emails}")
    private String mockEmailsPath;

    private final Set<String> processedMessageIds = ConcurrentHashMap.newKeySet();

    @Override
    public List<RawEmail> fetchNewMessages() {
        List<RawEmail> result = new ArrayList<>();
        Path dirPath = Paths.get(mockEmailsPath).toAbsolutePath().normalize();

        if (!Files.exists(dirPath) || !Files.isDirectory(dirPath)) {
            log.warn("Mock mailbox path does not exist or is not a directory: {}", dirPath);
            return result;
        }

        try (Stream<Path> stream = Files.walk(dirPath, 1)) {
            List<Path> emlFiles = stream
                    .filter(p -> Files.isRegularFile(p) && p.toString().toLowerCase().endsWith(".eml"))
                    .sorted()
                    .toList();

            log.info("Mock mailbox checking directory: {}. Found {} .eml files.", dirPath, emlFiles.size());

            for (Path path : emlFiles) {
                try {
                    byte[] bytes = Files.readAllBytes(path);
                    RawEmail rawEmail = emailParser.parse(bytes);
                    if (rawEmail != null) {
                        result.add(rawEmail);
                    }
                } catch (Exception e) {
                    log.error("Failed to parse mock email at {}: {}", path, e.getMessage(), e);
                }
            }
        } catch (IOException e) {
            log.error("Failed to list mock email directory {}: {}", dirPath, e.getMessage(), e);
        }

        return result;
    }

    @Override
    public void markProcessed(String messageId) {
        if (messageId != null) {
            processedMessageIds.add(messageId);
            log.debug("Mock mailbox marked message {} as processed", messageId);
        }
    }
}
