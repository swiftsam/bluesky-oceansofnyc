"""License plate OCR for NYC TLC plates."""

import re
from typing import Optional, List, Tuple
from pathlib import Path
import cv2
import numpy as np
import easyocr
from .matcher import get_potential_matches, validate_plate


class PlateOCR:
    """OCR for NYC TLC license plates (format: T######C)."""

    # NYC TLC plate pattern: T + 6 digits + C
    TLC_PATTERN = re.compile(r'^T\d{6}C$')

    def __init__(self, db_url: str = None):
        """
        Initialize OCR reader.

        Args:
            db_url: Database URL for TLC validation
        """
        self.db_url = db_url
        # Initialize EasyOCR reader for English
        # Use GPU if available, otherwise CPU
        self.reader = easyocr.Reader(['en'], gpu=True)

    def preprocess_image(self, image_path: str) -> np.ndarray:
        """
        Preprocess image for better OCR results.

        Args:
            image_path: Path to image file

        Returns:
            Preprocessed image as numpy array
        """
        # Read image
        img = cv2.imread(str(image_path))

        if img is None:
            raise ValueError(f"Could not read image: {image_path}")

        # Convert to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Apply bilateral filter to reduce noise while preserving edges
        denoised = cv2.bilateralFilter(gray, 11, 17, 17)

        # Apply adaptive thresholding
        thresh = cv2.adaptiveThreshold(
            denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY, 11, 2
        )

        return thresh

    def detect_yellow_regions(self, img: np.ndarray) -> np.ndarray:
        """
        Detect yellow/orange regions in image (NYC TLC plates are yellow).
        Uses multiple color spaces for robustness.

        Args:
            img: Input BGR image

        Returns:
            Binary mask of yellow regions
        """
        # Convert to HSV for better color detection
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

        # Wide yellow/orange range to handle different lighting conditions
        # TLC plates can appear quite different depending on:
        # - Sunlight vs shadow
        # - Time of day
        # - Camera settings
        # - Weathering of the plate
        lower_yellow = np.array([10, 30, 50])   # Very permissive lower bound
        upper_yellow = np.array([40, 255, 255])  # Wide upper bound

        # Create mask
        yellow_mask = cv2.inRange(hsv, lower_yellow, upper_yellow)

        # Clean up mask with morphological operations
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        yellow_mask = cv2.morphologyEx(yellow_mask, cv2.MORPH_CLOSE, kernel, iterations=2)
        yellow_mask = cv2.morphologyEx(yellow_mask, cv2.MORPH_OPEN, kernel)

        return yellow_mask

    def detect_plate_regions(self, image_path: str) -> List[Tuple[int, int, int, int]]:
        """
        Detect potential license plate regions in image.
        Uses combined approach: yellow color + edges + morphology.

        Args:
            image_path: Path to image file

        Returns:
            List of (x, y, w, h) tuples for potential plate regions
        """
        # Read original image
        img = cv2.imread(str(image_path))
        if img is None:
            return []

        img_height, img_width = img.shape[:2]
        plate_regions = []

        # Method 1: Yellow color detection
        yellow_mask = self.detect_yellow_regions(img)

        # Find contours in yellow regions
        contours, _ = cv2.findContours(
            yellow_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            aspect_ratio = w / float(h) if h > 0 else 0

            # Relaxed criteria for yellow regions
            if (2.0 <= aspect_ratio <= 7.0 and
                w >= 50 and h >= 15):
                plate_regions.append(('yellow', x, y, w, h, aspect_ratio))

        # Method 2: Edge detection fallback (always run)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Enhance contrast
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)

        # Edge detection
        edges = cv2.Canny(enhanced, 50, 150)

        # Morphological operations to connect edges
        kernel_rect = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 3))
        dilated = cv2.dilate(edges, kernel_rect, iterations=1)

        # Find contours
        contours, _ = cv2.findContours(
            dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            aspect_ratio = w / float(h) if h > 0 else 0

            if (2.5 <= aspect_ratio <= 7.0 and
                w >= 80 and h >= 15 and
                w <= img_width * 0.4):
                plate_regions.append(('edge', x, y, w, h, aspect_ratio))

        # Remove duplicates (regions that overlap significantly)
        unique_regions = []
        for method, x1, y1, w1, h1, ar in plate_regions:
            is_duplicate = False
            for _, x2, y2, w2, h2, _ in unique_regions:
                # Calculate overlap
                x_overlap = max(0, min(x1 + w1, x2 + w2) - max(x1, x2))
                y_overlap = max(0, min(y1 + h1, y2 + h2) - max(y1, y2))
                overlap_area = x_overlap * y_overlap

                area1 = w1 * h1
                area2 = w2 * h2
                min_area = min(area1, area2)

                # If more than 50% overlap, consider duplicate
                if overlap_area > 0.5 * min_area:
                    is_duplicate = True
                    break

            if not is_duplicate:
                unique_regions.append((method, x1, y1, w1, h1, ar))

        # Sort by detection method (yellow first) and then by area
        def sort_key(r):
            method, x, y, w, h, ar = r
            method_priority = 0 if method == 'yellow' else 1
            area = w * h
            return (method_priority, -area)

        unique_regions.sort(key=sort_key)

        # Return just the bbox tuples (without method and aspect ratio)
        return [(x, y, w, h) for _, x, y, w, h, _ in unique_regions[:10]]

    def extract_text_from_region(self, image_path: str,
                                 region: Optional[Tuple[int, int, int, int]] = None) -> List[str]:
        """
        Extract text from image or specific region using OCR.

        Args:
            image_path: Path to image file
            region: Optional (x, y, w, h) tuple to focus on specific region

        Returns:
            List of detected text strings
        """
        img = cv2.imread(str(image_path))

        # Crop to region if specified
        if region:
            x, y, w, h = region
            img = img[y:y+h, x:x+w]

        # Run OCR
        results = self.reader.readtext(img)

        # Extract text from results
        texts = [result[1] for result in results]
        return texts

    def clean_ocr_text(self, text: str) -> str:
        """
        Clean OCR text to match TLC plate format.
        Handles common OCR errors and tries to fix malformed plates.

        Args:
            text: Raw OCR text

        Returns:
            Cleaned text in TLC format (T######C)
        """
        # Remove spaces and special characters
        text = re.sub(r'[^A-Z0-9]', '', text.upper())

        if not text:
            return text

        # Common OCR corrections
        digit_corrections = {
            'O': '0',  # Letter O -> zero
            'I': '1',  # Letter I -> one
            'L': '1',  # Letter L -> one
            'Z': '2',
            'S': '5',
            'B': '8',
            'G': '6',
        }

        letter_corrections = {
            '0': 'O',  # Zero -> letter O
            '1': 'I',  # One -> letter I
            '4': 'A',  # Four -> letter A (sometimes)
        }

        # Try to fix TLC format
        # Expected: T + 6 digits + C

        # Case 1: Text is exactly 8 characters
        if len(text) == 8:
            cleaned = text[0]  # Keep first char
            # Clean middle 6 positions (should be digits)
            for char in text[1:7]:
                cleaned += digit_corrections.get(char, char)
            cleaned += text[7]  # Keep last char
            return cleaned

        # Case 2: Missing T or C (e.g., "879731C" or "T879731")
        if len(text) == 7:
            # Check if starts with digit - might be missing T
            if text[0].isdigit():
                # Try adding T at beginning
                cleaned = 'T' + text[:6]
                # Last char should be C
                if text[6].isdigit():
                    cleaned += 'C'
                else:
                    cleaned += text[6]
                return cleaned
            # Check if ends with digit - might be missing C
            elif text[6].isdigit():
                cleaned = text[0]
                for char in text[1:7]:
                    cleaned += digit_corrections.get(char, char)
                cleaned += 'C'
                return cleaned

        # Case 3: Text is 9+ digits (OCR misread T and/or C as digits)
        if len(text) >= 8 and text.isdigit():
            # Common patterns:
            # "1879731C" -> T at start became 1
            # "4879731C" -> T at start became 4
            # "T8797310" -> C at end became 0

            # Try fixing first character
            first_char = text[0]
            if first_char in ['1', '4', '7']:
                # Likely a misread T
                cleaned = 'T'
                # Get middle 6 digits
                middle = text[1:7] if len(text) >= 7 else text[1:]
                for char in middle:
                    cleaned += digit_corrections.get(char, char)
                # Fix last character
                if len(text) >= 8:
                    last_char = text[7]
                    if last_char in ['0', '1']:
                        cleaned += 'C'
                    else:
                        cleaned += last_char
                else:
                    cleaned += 'C'
                return cleaned

        # Case 4: Just return as-is with basic cleaning
        return text

    def validate_tlc_format(self, text: str) -> bool:
        """
        Check if text matches TLC plate format (T######C).

        Args:
            text: Text to validate

        Returns:
            True if matches TLC format
        """
        return bool(self.TLC_PATTERN.match(text))

    def extract_plate(self, image_path: str,
                     validate_db: bool = True) -> Optional[dict]:
        """
        Complete pipeline: segment, OCR, and validate license plate.

        Args:
            image_path: Path to image file
            validate_db: If True, validate against TLC database

        Returns:
            Dict with plate info: {
                'plate': str,
                'confidence': float,
                'valid_in_db': bool,
                'vehicle_info': Optional[tuple],
                'region': Optional[tuple]
            }
            Returns None if no valid plate found.
        """
        # Step 1: Detect potential plate regions
        regions = self.detect_plate_regions(image_path)

        # Step 2: Try OCR on each region
        best_result = None
        best_confidence = 0

        # First try detected regions
        for region in regions:
            texts = self.extract_text_from_region(image_path, region)

            for text in texts:
                cleaned = self.clean_ocr_text(text)

                # Check TLC format
                if self.validate_tlc_format(cleaned):
                    confidence = 0.8  # Base confidence for region detection + format match

                    if confidence > best_confidence:
                        best_result = {
                            'plate': cleaned,
                            'confidence': confidence,
                            'region': region
                        }
                        best_confidence = confidence

        # Also try full image if no regions found
        if not best_result:
            texts = self.extract_text_from_region(image_path)

            for text in texts:
                cleaned = self.clean_ocr_text(text)

                if self.validate_tlc_format(cleaned):
                    best_result = {
                        'plate': cleaned,
                        'confidence': 0.6,  # Lower confidence for full image
                        'region': None
                    }
                    break

        # Step 3: Validate against TLC database
        if best_result:
            if validate_db:
                is_valid, vehicle_info = validate_plate(best_result['plate'], self.db_url)
                best_result['valid_in_db'] = is_valid
                best_result['vehicle_info'] = vehicle_info

                # Boost confidence if found in database
                if is_valid:
                    best_result['confidence'] = min(best_result['confidence'] + 0.2, 1.0)
            else:
                best_result['valid_in_db'] = False
                best_result['vehicle_info'] = None

        return best_result

    def extract_plate_with_suggestions(self, image_path: str) -> dict:
        """
        Extract plate with fuzzy matching suggestions if not found in DB.

        Args:
            image_path: Path to image file

        Returns:
            Dict with plate info including suggestions if needed
        """
        result = self.extract_plate(image_path)

        if not result:
            return {
                'found': False,
                'message': 'No TLC plate detected in image'
            }

        # If found but not in database, try fuzzy matching
        if not result['valid_in_db']:
            plate = result['plate']

            # Try with wildcards for uncertain characters
            # Replace middle digits one at a time with wildcards
            suggestions = []
            for i in range(1, 7):  # Positions 1-6 are digits
                pattern = plate[:i] + '*' + plate[i+1:]
                matches = get_potential_matches(pattern, self.db_url, max_results=3)
                suggestions.extend(matches)

            # Remove duplicates while preserving order
            suggestions = list(dict.fromkeys(suggestions))[:5]

            result['suggestions'] = suggestions
            result['found'] = True
            result['message'] = f"Plate {plate} not found in database. Possible matches: {suggestions}"
        else:
            result['found'] = True
            result['message'] = f"Plate {result['plate']} validated successfully"
            result['suggestions'] = []

        return result
