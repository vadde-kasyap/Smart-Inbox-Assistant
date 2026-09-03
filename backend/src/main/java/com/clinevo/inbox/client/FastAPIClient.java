package com.clinevo.inbox.client;

import com.clinevo.inbox.dto.ai.AIProcessRequestDto;
import com.clinevo.inbox.dto.ai.AIProcessResponseDto;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.web.client.RestTemplateBuilder;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestTemplate;

import java.time.Duration;
import java.util.Map;

@Component
public class FastAPIClient implements AIClient {

    private static final Logger log = LoggerFactory.getLogger(FastAPIClient.class);

    private final RestTemplate restTemplate;
    private final String aiServiceUrl;

    public FastAPIClient(
            RestTemplateBuilder builder,
            @Value("${ai.service.url:http://ai-service:8000}") String aiServiceUrl) {
        this.aiServiceUrl = aiServiceUrl.endsWith("/") ? aiServiceUrl.substring(0, aiServiceUrl.length() - 1) : aiServiceUrl;
        this.restTemplate = builder
                .setConnectTimeout(Duration.ofSeconds(10))
                .setReadTimeout(Duration.ofSeconds(120))
                .build();
    }

    @Override
    public AIProcessResponseDto process(AIProcessRequestDto request) {
        String url = aiServiceUrl + "/ai/process";
        log.info("Sending AIProcessRequest for Job ID: {} to {}", request.getJobId(), url);

        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);
        HttpEntity<AIProcessRequestDto> entity = new HttpEntity<>(request, headers);

        try {
            ResponseEntity<AIProcessResponseDto> response = restTemplate.postForEntity(url, entity, AIProcessResponseDto.class);
            if (response.getStatusCode().is2xxSuccessful() && response.getBody() != null) {
                log.info("Received successful AIProcessResponse for Job ID: {}", request.getJobId());
                return response.getBody();
            } else {
                throw new RuntimeException("AI service returned non-2xx status: " + response.getStatusCode());
            }
        } catch (Exception e) {
            log.error("AI service request failed for Job ID {}: {}", request.getJobId(), e.getMessage(), e);
            throw new RuntimeException("AI processing failed: " + e.getMessage(), e);
        }
    }

    @Override
    public boolean healthCheck() {
        String url = aiServiceUrl + "/health";
        try {
            ResponseEntity<Map> resp = restTemplate.getForEntity(url, Map.class);
            return resp.getStatusCode().is2xxSuccessful();
        } catch (Exception e) {
            log.warn("AI service healthcheck failed: {}", e.getMessage());
            return false;
        }
    }
}
