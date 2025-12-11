#!/usr/bin/env python3
"""Run segmentation debug on all sighting images."""
import subprocess
from pathlib import Path

sightings_dir = Path("data/sightings")
output_dir = Path("debug_output")
output_dir.mkdir(exist_ok=True)

# Get all images
images = list(sightings_dir.glob("*.jpg")) + list(sightings_dir.glob("*.jpeg"))
images.sort()

print(f"Processing {len(images)} images...\n")

for i, img_path in enumerate(images, 1):
    print(f"[{i}/{len(images)}] {img_path.name}")

    # Run debug command
    result = subprocess.run(
        ["uv", "run", "python", "-m", "validate.cli", "debug", str(img_path), "--output", "./debug_output"],
        capture_output=True,
        text=True
    )

    # Print Found/Region lines
    for line in result.stdout.split('\n'):
        if line.startswith(('Found', 'Region', '💾')):
            print(f"  {line}")

    print()

print(f"\n✅ Done! Check debug_output/ for results")
