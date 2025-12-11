#!/usr/bin/env python3
"""Test OCR on the 7 successful detections."""
import subprocess
from pathlib import Path

# Map debug files back to original images
debug_files = list(Path("debug_output").glob("debug_*.jpg")) + list(Path("debug_output").glob("debug_*.jpeg"))

# Extract original filenames
original_images = []
for debug_file in debug_files:
    # Remove 'debug_' prefix
    original_name = debug_file.name.replace('debug_', '')

    # Find the original file
    sightings_path = Path("data/sightings") / original_name
    if sightings_path.exists():
        original_images.append(sightings_path)

print(f"Running OCR on {len(original_images)} images with successful plate detection...\n")

for i, img_path in enumerate(original_images, 1):
    print(f"{'='*70}")
    print(f"[{i}/{len(original_images)}] {img_path.name}")
    print(f"{'='*70}")

    # Run extract command with suggestions
    result = subprocess.run(
        ["uv", "run", "python", "-m", "validate.cli", "extract", str(img_path), "--suggestions"],
        capture_output=True,
        text=True
    )

    # Print output (filter warnings)
    for line in result.stdout.split('\n'):
        if 'UserWarning' not in line and 'pin_memory' not in line and line.strip():
            print(line)

    if result.stderr and 'UserWarning' not in result.stderr:
        print(f"Error: {result.stderr[:200]}")

    print()

print(f"\n✅ Done!")
