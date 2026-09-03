-- =====================================================================
-- Smart Inbox Assistant — Seed / Verification Data
-- Synthetic non-production data only
-- =====================================================================

INSERT INTO EMAIL (id, message_id, sender_email, subject, body, received_at, status)
VALUES (1, '<seed-icsr-001@synthetic.clinevo.local>', 'dr.smith@syntheticclinic.org', 'Spontaneous ICSR: SynthoStatin Rash', 'Patient experienced mild erythematous rash following 20mg SynthoStatin.', SYSTIMESTAMP - INTERVAL '1' HOUR, 'RECEIVED');

INSERT INTO ATTACHMENT (id, email_id, filename, content_type, file_size, storage_reference, sha256_hash, is_pdf, status)
VALUES (1, 1, 'case_report_syntho.pdf', 'application/pdf', 14250, '/app/storage/1/case_report_syntho.pdf', 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', 1, 'QUEUED');

INSERT INTO PROCESSING_JOB (id, attachment_id, status, retry_count, max_retries, queued_at)
VALUES (1, 1, 'QUEUED', 0, 3, SYSTIMESTAMP);

INSERT INTO AUDIT_LOG (email_id, job_id, actor_type, actor_id, action, metadata, timestamp)
VALUES (1, 1, 'SYSTEM', 'SEEDED', 'EMAIL_RECEIVED', '{"source":"seed_script"}', SYSTIMESTAMP);

COMMIT;
