-- Add pending_borough column to chat_sessions table
-- Migration: Add borough field to session state tracking

ALTER TABLE chat_sessions
ADD COLUMN IF NOT EXISTS pending_borough VARCHAR(20);
