package com.clinevo.inbox.service.storage;

public interface StorageService {
    String store(Long emailId, String filename, byte[] content);
    byte[] load(String storageReference);
    void delete(String storageReference);
    String computeSha256(byte[] content);
}
