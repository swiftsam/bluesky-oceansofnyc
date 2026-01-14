"""Extract structured data from user messages."""

import re


def extract_plate_from_text(text: str) -> str | None:
    """
    Extract a license plate from user text.

    Matches NYC TLC plate formats:
    - T######C (full format, e.g., T123456C)
    - ###### (6 digits only, will be normalized to T######C)
    - T###### (missing C suffix)
    - ######C (missing T prefix)

    Args:
        text: User's message text

    Returns:
        Normalized plate (T######C format) or None if no valid plate found
    """
    if not text:
        return None

    text = text.strip().upper()

    # Pattern 1: Full format T######C
    match = re.search(r"\bT(\d{6})C\b", text)
    if match:
        return f"T{match.group(1)}C"

    # Pattern 2: Just 6 digits
    match = re.search(r"\b(\d{6})\b", text)
    if match:
        return f"T{match.group(1)}C"

    # Pattern 3: T###### (missing C suffix)
    match = re.search(r"\bT(\d{6})\b", text)
    if match:
        return f"T{match.group(1)}C"

    # Pattern 4: ######C (missing T prefix)
    match = re.search(r"\b(\d{6})C\b", text)
    if match:
        return f"T{match.group(1)}C"

    return None


def extract_borough_from_text(text: str) -> str | None:
    """
    Extract a borough from user text.

    Uses the existing borough parser to detect borough names or abbreviations
    anywhere in the text.

    Args:
        text: User's message text

    Returns:
        Canonical borough name or None if not found
    """
    if not text:
        return None

    from geolocate.boroughs import parse_borough_input

    # Try to parse the whole text first
    borough = parse_borough_input(text)
    if borough:
        return borough

    # Try to find borough keywords in the text
    text_upper = text.upper()

    # Look for common patterns like "in Brooklyn" or "Brooklyn"
    borough_keywords = {
        "BROOKLYN": "Brooklyn",
        "MANHATTAN": "Manhattan",
        "QUEENS": "Queens",
        "BRONX": "Bronx",
        "STATEN ISLAND": "Staten Island",
        "BK": "Brooklyn",  # Common abbreviation
    }

    for keyword, canonical in borough_keywords.items():
        if keyword in text_upper:
            return canonical

    # Look for single letter indicators (only if isolated, not part of a plate)
    # Match single letters that are word boundaries
    for letter, canonical in [
        ("B", "Brooklyn"),
        ("M", "Manhattan"),
        ("Q", "Queens"),
        ("X", "Bronx"),
        ("S", "Staten Island"),
    ]:
        # Use word boundary to avoid matching letters in plates
        if re.search(rf"\b{letter}\b", text_upper):
            return canonical

    return None
