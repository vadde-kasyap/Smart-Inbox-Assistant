package com.clinevo.inbox.queue;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import java.util.concurrent.ArrayBlockingQueue;
import java.util.concurrent.BlockingQueue;
import java.util.concurrent.TimeUnit;

@Component
public class JobQueue {

    private static final Logger log = LoggerFactory.getLogger(JobQueue.class);
    private final BlockingQueue<Long> queue;

    public JobQueue(@Value("${queue.capacity:1000}") int capacity) {
        this.queue = new ArrayBlockingQueue<>(capacity);
        log.info("Initialized in-process JobQueue with capacity {}", capacity);
    }

    public boolean enqueue(Long jobId) {
        if (jobId == null) {
            return false;
        }
        boolean offered = queue.offer(jobId);
        if (offered) {
            log.info("Enqueued Job ID: {}. Queue size: {}", jobId, queue.size());
        } else {
            log.error("Failed to enqueue Job ID: {} - Queue is full! (size={})", jobId, queue.size());
        }
        return offered;
    }

    public Long take() throws InterruptedException {
        return queue.take();
    }

    public Long poll(long timeout, TimeUnit unit) throws InterruptedException {
        return queue.poll(timeout, unit);
    }

    public int size() {
        return queue.size();
    }

    public boolean isEmpty() {
        return queue.isEmpty();
    }
}
