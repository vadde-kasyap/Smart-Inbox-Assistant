-- =====================================================================
-- Reset / Truncate Script for Clean Ingestion
-- =====================================================================

DELETE FROM SOURCE_REFERENCE;
DELETE FROM EXTRACTED_FIELD;
DELETE FROM CLASSIFICATION;
DELETE FROM IMAGE_RESULT;
DELETE FROM PROCESSING_METRICS;
DELETE FROM AI_RESULT;
DELETE FROM AUDIT_LOG;
DELETE FROM PROCESSING_JOB;
DELETE FROM ATTACHMENT;
DELETE FROM EMAIL;

COMMIT;
