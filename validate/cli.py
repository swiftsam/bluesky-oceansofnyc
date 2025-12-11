"""CLI for license plate OCR and validation."""

import click
import json
from pathlib import Path
from .plate_ocr import PlateOCR


@click.group()
def cli():
    """TLC License Plate OCR and Validation."""
    pass


@cli.command()
@click.argument('image_path', type=click.Path(exists=True))
@click.option('--db-url', envvar='DATABASE_URL', help='Database URL for validation')
@click.option('--no-validate', is_flag=True, help='Skip database validation')
@click.option('--suggestions', is_flag=True, help='Show suggestions if plate not found')
@click.option('--json-output', is_flag=True, help='Output results as JSON')
def extract(image_path, db_url, no_validate, suggestions, json_output):
    """Extract license plate from an image."""
    ocr = PlateOCR(db_url)

    if suggestions:
        result = ocr.extract_plate_with_suggestions(image_path)
    else:
        result = ocr.extract_plate(image_path, validate_db=not no_validate)

    if json_output:
        # Convert result to JSON-serializable format
        if result:
            output = {
                'plate': result.get('plate'),
                'confidence': result.get('confidence'),
                'valid_in_db': result.get('valid_in_db'),
                'message': result.get('message', ''),
                'suggestions': result.get('suggestions', [])
            }
        else:
            output = {'found': False, 'message': 'No plate detected'}

        click.echo(json.dumps(output, indent=2))
    else:
        if not result or not result.get('found', True):
            click.echo("❌ No TLC plate detected in image")
            return

        plate = result.get('plate')
        confidence = result.get('confidence', 0)
        valid = result.get('valid_in_db', False)

        click.echo(f"\n🚗 License Plate: {plate}")
        click.echo(f"   Confidence: {confidence:.1%}")

        if valid:
            click.echo(f"   ✅ Valid in TLC database")

            if result.get('vehicle_info'):
                vehicle = result['vehicle_info']
                click.echo(f"\n   Vehicle Details:")
                click.echo(f"   - VIN: {vehicle[7] if len(vehicle) > 7 else 'N/A'}")
                click.echo(f"   - Year: {vehicle[11] if len(vehicle) > 11 else 'N/A'}")
                click.echo(f"   - Base: {vehicle[13] if len(vehicle) > 13 else 'N/A'}")
        else:
            click.echo(f"   ⚠️  Not found in TLC database")

            if result.get('suggestions'):
                click.echo(f"\n   Possible matches:")
                for suggestion in result['suggestions']:
                    click.echo(f"   - {suggestion}")


@cli.command()
@click.argument('directory', type=click.Path(exists=True))
@click.option('--db-url', envvar='DATABASE_URL', help='Database URL for validation')
@click.option('--output', type=click.Path(), help='Output JSON file with results')
@click.option('--extensions', default='jpg,jpeg,png', help='Image file extensions to process')
def batch(directory, db_url, output, extensions):
    """Process multiple images in a directory."""
    ocr = PlateOCR(db_url)

    # Get all image files
    ext_list = extensions.split(',')
    image_files = []
    for ext in ext_list:
        image_files.extend(Path(directory).glob(f"*.{ext.strip()}"))

    click.echo(f"Processing {len(image_files)} images...")

    results = []
    with click.progressbar(image_files) as bar:
        for image_path in bar:
            result = ocr.extract_plate_with_suggestions(str(image_path))

            if result and result.get('found'):
                results.append({
                    'image': str(image_path),
                    'plate': result.get('plate'),
                    'confidence': result.get('confidence'),
                    'valid_in_db': result.get('valid_in_db'),
                    'suggestions': result.get('suggestions', [])
                })

    # Print summary
    click.echo(f"\n✅ Successfully extracted {len(results)} plates")

    valid_count = sum(1 for r in results if r['valid_in_db'])
    click.echo(f"   {valid_count} validated in TLC database")

    # Save to file if specified
    if output:
        with open(output, 'w') as f:
            json.dump(results, f, indent=2)
        click.echo(f"\n💾 Results saved to {output}")
    else:
        # Print results
        click.echo("\nResults:")
        for result in results:
            status = "✅" if result['valid_in_db'] else "⚠️ "
            click.echo(f"{status} {result['image']}: {result['plate']} ({result['confidence']:.1%})")


@cli.command()
@click.argument('image_path', type=click.Path(exists=True))
@click.option('--output', type=click.Path(), help='Output directory for debug images')
def debug(image_path, output):
    """Show detected regions for debugging."""
    import cv2

    ocr = PlateOCR()

    # Detect regions
    regions = ocr.detect_plate_regions(image_path)

    click.echo(f"Found {len(regions)} potential plate regions:")

    # Draw regions on image
    img = cv2.imread(str(image_path))

    for i, (x, y, w, h) in enumerate(regions, 1):
        click.echo(f"\nRegion {i}: x={x}, y={y}, w={w}, h={h}, aspect={w/h:.2f}")

        # Draw rectangle
        cv2.rectangle(img, (x, y), (x + w, y + h), (0, 255, 0), 2)
        cv2.putText(img, f"#{i}", (x, y - 10),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)

        # Try OCR on this region
        texts = ocr.extract_text_from_region(image_path, (x, y, w, h))
        if texts:
            click.echo(f"   OCR: {texts}")

    # Save or show image
    if output:
        output_path = Path(output)
        output_path.mkdir(exist_ok=True)
        out_file = output_path / f"debug_{Path(image_path).name}"
        cv2.imwrite(str(out_file), img)
        click.echo(f"\n💾 Debug image saved to {out_file}")
    else:
        click.echo("\nClose the image window to continue...")
        cv2.imshow('Detected Regions', img)
        cv2.waitKey(0)
        cv2.destroyAllWindows()


if __name__ == '__main__':
    cli()
