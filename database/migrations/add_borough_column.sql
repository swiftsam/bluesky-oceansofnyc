-- Add borough column to sightings table
-- Migration: Add borough field to simplify location collection

-- Add borough column (nullable to support existing data)
ALTER TABLE sightings
ADD COLUMN IF NOT EXISTS borough VARCHAR(20);

-- Backfill borough from existing lat/lon data
-- This will be handled by Python script for more accurate reverse geocoding
