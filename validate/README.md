# TLC License Plate OCR

Automated license plate recognition for NYC TLC plates (format: `T######C`).

## Features

### 1. License Plate Segmentation
- Uses OpenCV edge detection and contour analysis
- Filters by aspect ratio (2:1 to 6:1) to find plate-like rectangles
- Returns top candidate regions sorted by area

### 2. OCR with Pattern Validation
- Uses EasyOCR pre-trained models for text recognition
- Automatically corrects common OCR errors (O→0, I→1, S→5, etc.)
- Validates against TLC format: `T` + 6 digits + `C`

### 3. TLC Database Validation
- Validates extracted plates against your TLC database
- Provides fuzzy matching with wildcard patterns for uncertain characters
- Returns vehicle information if found in database

## Installation

Install the new dependencies:

```bash
uv pip install -e .
```

This will install:
- `easyocr` - OCR engine with pre-trained models
- `opencv-python` - Computer vision for image processing

## Usage

### CLI Commands

#### Extract plate from single image

```bash
tlc-ocr extract /path/to/image.jpg
```

With suggestions for uncertain matches:

```bash
tlc-ocr extract /path/to/image.jpg --suggestions
```

JSON output:

```bash
tlc-ocr extract /path/to/image.jpg --json-output
```

#### Batch process multiple images

```bash
tlc-ocr batch /path/to/images/directory
```

Save results to JSON:

```bash
tlc-ocr batch /path/to/images/directory --output results.json
```

#### Debug mode (visualize detected regions)

```bash
tlc-ocr debug /path/to/image.jpg --output ./debug_output
```

### Python API

```python
from validate.plate_ocr import PlateOCR

# Initialize OCR
ocr = PlateOCR(db_url="postgresql://...")

# Extract and validate plate
result = ocr.extract_plate_with_suggestions("image.jpg")

if result['found']:
    print(f"Plate: {result['plate']}")
    print(f"Confidence: {result['confidence']:.1%}")
    print(f"Valid in DB: {result['valid_in_db']}")

    if result['suggestions']:
        print(f"Suggestions: {result['suggestions']}")
```

## How It Works

### Step 1: Image Preprocessing
- Convert to grayscale
- Apply bilateral filter to reduce noise
- Apply adaptive thresholding

### Step 2: Plate Region Detection
- Edge detection using Canny
- Contour detection to find rectangles
- Filter by aspect ratio and size
- Return top 5 candidates

### Step 3: OCR Extraction
- Run EasyOCR on detected regions
- Clean text (remove spaces, special chars)
- Apply common OCR corrections for license plates
- Validate against TLC pattern

### Step 4: Database Validation
- Check exact match in TLC database
- If not found, generate wildcard patterns
- Search for similar plates
- Return top matches

## Configuration

### GPU Support

EasyOCR will automatically use GPU if available (faster processing). To force CPU:

```python
ocr = PlateOCR(db_url="...")
ocr.reader = easyocr.Reader(['en'], gpu=False)
```

### Pattern Matching

The OCR corrects common errors for the digit positions (1-6):

- `O` → `0` (letter O to zero)
- `I` → `1` (letter I to one)
- `Z` → `2`
- `S` → `5`
- `B` → `8`
- `G` → `6`

First and last positions (`T` and `C`) are preserved.

## Examples

### Example 1: Successful extraction

```bash
$ tlc-ocr extract data/sightings/PXL_20251024_113832642.jpg

🚗 License Plate: T731580C
   Confidence: 100.0%
   ✅ Valid in TLC database

   Vehicle Details:
   - VIN: VCF1CSZB0RC123456
   - Year: 2024
   - Base: REVEL TRANSIT INC
```

### Example 2: Uncertain match with suggestions

```bash
$ tlc-ocr extract image.jpg --suggestions

🚗 License Plate: T73B580C
   Confidence: 80.0%
   ⚠️  Not found in TLC database

   Possible matches:
   - T731580C
   - T738580C
   - T732580C
```

### Example 3: Batch processing

```bash
$ tlc-ocr batch data/sightings/ --output results.json

Processing 40 images...
✅ Successfully extracted 38 plates
   35 validated in TLC database

💾 Results saved to results.json
```

## Troubleshooting

### No plate detected

Try the debug mode to see what regions were detected:

```bash
tlc-ocr debug image.jpg
```

### Low confidence / wrong plate

Common issues:
- Image quality too low
- Plate at extreme angle
- Plate too small in frame
- Glare or reflections on plate

Solutions:
- Crop image to focus on plate area
- Improve image resolution
- Adjust lighting/contrast

### GPU not working

Install CUDA-enabled PyTorch:

```bash
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
```

Or force CPU mode in your code.
