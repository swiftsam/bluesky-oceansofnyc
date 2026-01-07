-- Add image URL fields to chat_sessions table
-- Allows session to store original and web image paths during conversation flow

ALTER TABLE chat_sessions
ADD COLUMN IF NOT EXISTS pending_image_path_original TEXT,
ADD COLUMN IF NOT EXISTS pending_image_url_web TEXT;

COMMENT ON COLUMN chat_sessions.pending_image_path IS 'Path to image in Modal volume (for Bluesky posting)';
COMMENT ON COLUMN chat_sessions.pending_image_path_original IS 'Path to original full-resolution image in Modal volume';
COMMENT ON COLUMN chat_sessions.pending_image_url_web IS 'Public URL to web-optimized image in R2 storage';
