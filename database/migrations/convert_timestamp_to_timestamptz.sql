-- Migration: Convert sightings.timestamp from TEXT to TIMESTAMPTZ
--
-- Current state: timestamp column stores ISO strings in inconsistent formats:
--   - '2026-01-16 17:21:42.812545' (space separator)
--   - '2026-01-16T13:51:16' (ISO format with T)
--
-- Target state: TIMESTAMPTZ column for proper timestamp handling
--
-- Benefits:
--   - Consistent storage format
--   - Proper indexing and date comparisons
--   - Timezone-aware (stores in UTC)
--   - No format ambiguity

-- Step 1: Add new column with proper type
ALTER TABLE sightings ADD COLUMN IF NOT EXISTS timestamp_new TIMESTAMPTZ;

-- Step 2: Migrate data - PostgreSQL handles both formats
-- The ::timestamptz cast works with both 'T' separator and space separator
UPDATE sightings
SET timestamp_new = timestamp::timestamptz
WHERE timestamp IS NOT NULL AND timestamp_new IS NULL;

-- Step 3: Drop old column and rename new one
-- NOTE: Run this only after verifying the migration was successful
-- ALTER TABLE sightings DROP COLUMN timestamp;
-- ALTER TABLE sightings RENAME COLUMN timestamp_new TO timestamp;

-- Verification query (run before dropping old column):
-- SELECT id, timestamp as old_text, timestamp_new as new_timestamptz
-- FROM sightings
-- WHERE timestamp IS NOT NULL
-- LIMIT 10;
