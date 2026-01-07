-- Add web URL fields for R2-hosted images
-- This migration adds columns to track both original and web-accessible image paths

ALTER TABLE sightings
ADD COLUMN IF NOT EXISTS image_path_original TEXT,
ADD COLUMN IF NOT EXISTS image_url_web TEXT;

-- Migrate existing image_path to image_path_original
-- (image_path will continue to be used for Modal volume paths)
UPDATE sightings
SET image_path_original = image_path
WHERE image_path_original IS NULL AND image_path IS NOT NULL;

COMMENT ON COLUMN sightings.image_path IS 'Path to image in Modal volume (for Bluesky posting, local processing)';
COMMENT ON COLUMN sightings.image_path_original IS 'Path to original full-resolution image in Modal volume';
COMMENT ON COLUMN sightings.image_url_web IS 'Public URL to web-optimized image in R2 storage';
