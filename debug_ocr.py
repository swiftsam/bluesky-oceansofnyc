#!/usr/bin/env python3
"""Debug OCR to see what text is being extracted."""
from validate.plate_ocr import PlateOCR
from pathlib import Path

# Test on one image that we know has a visible plate
test_image = "data/sightings/bafkreidowwr5iwj3zudoxqe3j6ruexpeai7qflf2n4hnkzgyoxbw3lb66q.jpg"

print(f"Testing OCR on: {test_image}\n")

ocr = PlateOCR()

# Step 1: Get detected regions
regions = ocr.detect_plate_regions(test_image)
print(f"Detected {len(regions)} regions:")
for i, (x, y, w, h) in enumerate(regions, 1):
    aspect = w/h if h > 0 else 0
    print(f"  Region {i}: x={x}, y={y}, w={w}, h={h}, aspect={aspect:.2f}")

# Step 2: Try OCR on each region
print(f"\nRunning OCR on each region:")
for i, region in enumerate(regions, 1):
    texts = ocr.extract_text_from_region(test_image, region)
    print(f"\n  Region {i} OCR results:")
    if texts:
        for j, text in enumerate(texts, 1):
            print(f"    {j}. Raw: '{text}'")
            cleaned = ocr.clean_ocr_text(text)
            print(f"       Cleaned: '{cleaned}'")
            is_valid = ocr.validate_tlc_format(cleaned)
            print(f"       Valid TLC format: {is_valid}")
    else:
        print("    (no text detected)")

# Step 3: Try OCR on full image
print(f"\n\nRunning OCR on full image:")
texts = ocr.extract_text_from_region(test_image)
print(f"Found {len(texts)} text regions:")
for i, text in enumerate(texts[:10], 1):  # Limit to first 10
    print(f"  {i}. Raw: '{text}'")
    cleaned = ocr.clean_ocr_text(text)
    print(f"     Cleaned: '{cleaned}'")
    is_valid = ocr.validate_tlc_format(cleaned)
    if is_valid:
        print(f"     ✅ VALID TLC FORMAT!")
