-- Migration: Drop old image columns after successful migration to unified filename
-- Part of image storage cleanup (Phase 7)

-- Drop old columns from sightings table
ALTER TABLE sightings DROP COLUMN IF EXISTS image_path_original;
ALTER TABLE sightings DROP COLUMN IF EXISTS image_url_web;
ALTER TABLE sightings DROP COLUMN IF EXISTS image_path;

-- Drop old columns from chat_sessions table
ALTER TABLE chat_sessions DROP COLUMN IF EXISTS pending_image_path_original;
ALTER TABLE chat_sessions DROP COLUMN IF EXISTS pending_image_url_web;
