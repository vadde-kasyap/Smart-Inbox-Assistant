package com.clinevo.inbox.service.storage;

import com.clinevo.inbox.exception.StorageException;
import jakarta.annotation.PostConstruct;
import org.apache.commons.codec.digest.DigestUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.nio.file.StandardOpenOption;

@Service
public class FileSystemStorageService implements StorageService {

    private static final Logger log = LoggerFactory.getLogger(FileSystemStorageService.class);

    private final Path rootLocation;

    public FileSystemStorageService(@Value("${app.storage.path:./storage}") String storagePath) {
        this.rootLocation = Paths.get(storagePath).toAbsolutePath().normalize();
    }

    @PostConstruct
    public void init() {
        try {
            Files.createDirectories(rootLocation);
            log.info("Initialized file storage at: {}", rootLocation);
        } catch (IOException e) {
            throw new StorageException("Could not initialize storage directory: " + rootLocation, e);
        }
    }

    @Override
    public String store(Long emailId, String filename, byte[] content) {
        try {
            String safeFilename = Paths.get(filename).getFileName().toString();
            Path emailDir = rootLocation.resolve(String.valueOf(emailId));
            Files.createDirectories(emailDir);

            Path targetPath = emailDir.resolve(safeFilename);
            Files.write(targetPath, content, StandardOpenOption.CREATE, StandardOpenOption.TRUNCATE_EXISTING);
            log.debug("Stored attachment for email {} at: {}", emailId, targetPath);
            return targetPath.toString();
        } catch (IOException e) {
            throw new StorageException("Failed to store file " + filename, e);
        }
    }

    @Override
    public byte[] load(String storageReference) {
        try {
            Path path = Paths.get(storageReference);
            if (!Files.exists(path)) {
                throw new StorageException("File not found at: " + storageReference);
            }
            return Files.readAllBytes(path);
        } catch (IOException e) {
            throw new StorageException("Failed to read file from " + storageReference, e);
        }
    }

    @Override
    public void delete(String storageReference) {
        try {
            Path path = Paths.get(storageReference);
            Files.deleteIfExists(path);
        } catch (IOException e) {
            log.warn("Could not delete file at: {}", storageReference, e);
        }
    }

    @Override
    public String computeSha256(byte[] content) {
        if (content == null || content.length == 0) {
            return DigestUtils.sha256Hex(new byte[0]);
        }
        return DigestUtils.sha256Hex(content);
    }
}
