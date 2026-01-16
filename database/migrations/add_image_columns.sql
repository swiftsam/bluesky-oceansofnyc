-- Migration: Add image_timestamp and image_filename columns
-- Part of image storage cleanup migration

-- Add image_timestamp (proper TIMESTAMPTZ from EXIF data)
ALTER TABLE sightings ADD COLUMN IF NOT EXISTS image_timestamp TIMESTAMPTZ;

-- Add image_filename (new unified filename format: {plate}_{yyyymmdd_hhmmss_ssss}.jpg)
ALTER TABLE sightings ADD COLUMN IF NOT EXISTS image_filename TEXT;

-- Backfill image_timestamp from existing timestamp column where parseable
-- Note: existing timestamp column is stored as TEXT in ISO format
UPDATE sightings
SET image_timestamp = timestamp::timestamptz
WHERE image_timestamp IS NULL AND timestamp IS NOT NULL;

-- Add comments for documentation
COMMENT ON COLUMN sightings.image_timestamp IS 'Timestamp when image was taken (from EXIF DateTimeOriginal)';
COMMENT ON COLUMN sightings.image_filename IS 'Unified filename: {plate}_{yyyymmdd_hhmmss_ssss}.jpg';

-- Add pending_image_timestamp to chat_sessions for SMS flow
ALTER TABLE chat_sessions ADD COLUMN IF NOT EXISTS pending_image_timestamp TIMESTAMPTZ;
COMMENT ON COLUMN chat_sessions.pending_image_timestamp IS 'EXIF timestamp of pending image (for filename generation)';
