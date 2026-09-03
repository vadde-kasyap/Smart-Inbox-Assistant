package com.clinevo.inbox.client;

import com.clinevo.inbox.dto.ai.AIProcessRequestDto;
import com.clinevo.inbox.dto.ai.AIProcessResponseDto;

public interface AIClient {
    AIProcessResponseDto process(AIProcessRequestDto request);
    boolean healthCheck();
}
