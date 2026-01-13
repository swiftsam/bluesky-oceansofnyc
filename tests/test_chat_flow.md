# Chat Flow Test Scenarios

## Scenario 1: Everything in one message (GPS)
**User sends:** [Image with GPS] + "T123456C"
**Result:** Sighting saved immediately
**Messages:** 1 (confirmation)

## Scenario 2: Everything in one message (no GPS)
**User sends:** [Image without GPS] + "T123456C in Brooklyn"
**Result:** Sighting saved immediately
**Messages:** 1 (confirmation)

## Scenario 3: Image + plate, ask for location
**User sends:** [Image without GPS] + "T123456C"
**Result:** Ask for borough
**Messages:** 2 (borough request + confirmation after user replies)

## Scenario 4: Image only, ask for plate
**User sends:** [Image with GPS]
**Result:** Ask for plate
**Messages:** 2 (plate request + confirmation after user replies)

## Scenario 5: Image only (no GPS), ask for plate then location
**User sends:** [Image without GPS]
**Bot asks:** "What's the license plate?"
**User sends:** "T123456C"
**Bot asks:** "Which borough?"
**User sends:** "Brooklyn"
**Result:** Sighting saved
**Messages:** 3 (plate request + borough request + confirmation)

## Scenario 6: Plate and borough in follow-up message
**User sends:** [Image without GPS]
**Bot asks:** "What's the license plate?"
**User sends:** "T123456C in Brooklyn"
**Result:** Sighting saved immediately (both extracted)
**Messages:** 2 (plate request + confirmation)

## Old Flow Comparison

### Old: Always 3 messages minimum (no GPS)
1. User: [Image]
2. Bot: "What's the plate?"
3. User: "T123456C"
4. Bot: "Which borough?"
5. User: "Brooklyn"
6. Bot: Confirmation

### New: Can be 1 message
1. User: [Image] "T123456C in Brooklyn"
2. Bot: Confirmation

## Benefits
- Experienced users can submit in one message
- Less back-and-forth for all users
- More flexible - extracts whatever information is available
- Backwards compatible - still prompts when info is missing
