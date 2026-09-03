package com.clinevo.inbox.controller;

import com.clinevo.inbox.dto.ApiResponse;
import com.clinevo.inbox.dto.review.ReviewAcceptRequest;
import com.clinevo.inbox.dto.review.ReviewDetailDto;
import com.clinevo.inbox.dto.review.ReviewOverrideRequest;
import com.clinevo.inbox.dto.review.ReviewQueueItemDto;
import com.clinevo.inbox.entity.EmailStatus;
import com.clinevo.inbox.service.ReviewService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/review-items")
@RequiredArgsConstructor
public class ReviewController {

    private final ReviewService reviewService;

    @GetMapping
    public ResponseEntity<ApiResponse<List<ReviewQueueItemDto>>> getReviewQueue(
            @RequestParam(required = false) String category,
            @RequestParam(required = false) EmailStatus status,
            @RequestParam(required = false) String search) {
        List<ReviewQueueItemDto> items = reviewService.getReviewQueue(category, status, search);
        return ResponseEntity.ok(ApiResponse.ok(items));
    }

    @GetMapping("/{emailId}")
    public ResponseEntity<ApiResponse<ReviewDetailDto>> getReviewDetail(@PathVariable Long emailId) {
        ReviewDetailDto detail = reviewService.getReviewDetail(emailId);
        return ResponseEntity.ok(ApiResponse.ok(detail));
    }

    @PostMapping("/{emailId}/accept")
    public ResponseEntity<ApiResponse<ReviewDetailDto>> acceptReview(
            @PathVariable Long emailId,
            @RequestBody(required = false) ReviewAcceptRequest request) {
        ReviewDetailDto updated = reviewService.acceptReview(emailId, request);
        return ResponseEntity.ok(ApiResponse.ok("Review accepted successfully", updated));
    }

    @PostMapping("/{emailId}/override")
    public ResponseEntity<ApiResponse<ReviewDetailDto>> overrideReview(
            @PathVariable Long emailId,
            @RequestBody ReviewOverrideRequest request) {
        ReviewDetailDto updated = reviewService.overrideReview(emailId, request);
        return ResponseEntity.ok(ApiResponse.ok("Review override applied successfully", updated));
    }
}
