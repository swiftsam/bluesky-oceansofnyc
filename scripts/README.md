# Scripts

Utility scripts for database maintenance and operations.

## consolidate_contributors.py

Consolidates duplicate contributor identities by transferring all sightings from one contributor to another.

### Usage

```bash
python scripts/consolidate_contributors.py <eliminate_id> <retain_id>
```

**Arguments:**
- `eliminate_id` - The contributor ID that will lose all sightings
- `retain_id` - The contributor ID that will gain all sightings

**What it does:**
1. Looks up both contributors and displays their information
2. Shows current sighting counts for each
3. Asks for confirmation before proceeding
4. Updates all sightings from `eliminate_id` to `retain_id`
5. Leaves the eliminated contributor in the database (delete manually if needed)

**Example:**

```bash
python scripts/consolidate_contributors.py 42 17
```

This will transfer all sightings from contributor 42 to contributor 17.

**Output example:**

```
======================================================================
CONTRIBUTOR CONSOLIDATION
======================================================================

📤 CONTRIBUTOR TO ELIMINATE (ID: 42)
   Phone Number:    +14123342330
   Bluesky Handle:  None
   Preferred Name:  None
   Display Name:    (anonymous)
   Sighting Count:  5

📥 CONTRIBUTOR TO RETAIN (ID: 17)
   Phone Number:    +14123342330
   Bluesky Handle:  @user.bsky.social
   Preferred Name:  John Doe
   Display Name:    John Doe
   Sighting Count:  12

======================================================================

After consolidation, contributor 17 will have 17 sightings.
Contributor 42 will remain in the database but have 0 sightings.

Do you want to proceed with this consolidation? (yes/no):
```

### Common Use Cases

1. **Same person, different contact methods**: User submitted via SMS initially (phone only), then later via Bluesky (added handle)
2. **Multiple phone numbers**: Same person accidentally used different phone numbers
3. **Typos or variations**: Same person with slightly different identifier formats

### Safety Features

- Displays detailed information before making changes
- Requires explicit "yes" confirmation
- Shows updated counts after consolidation
- Does NOT delete the eliminated contributor record (manual cleanup required)

## Other Scripts

### backfill_boroughs.py
Backfills borough values for sightings with GPS coordinates.

### backfill_image_hashes.py
Backfills SHA-256 and perceptual hashes for existing sighting images.

### recover_sessions.py
Recovers incomplete chat sessions from the database.
