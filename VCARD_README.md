# Oceans of NYC vCard Files

Two vCard files have been generated for easy contact sharing:

## Files

1. **oceansofnyc.vcf** (62KB) - Full vCard with embedded logo
   - Contains 200x200px logo embedded as base64
   - Larger QR code when used
   - Logo displays in contact apps

2. **oceansofnyc_simple.vcf** (382 bytes) - Simple vCard without logo
   - Much smaller file size
   - Simpler QR code
   - Faster to scan

## What's Included

Both files contain:
- Name: Oceans of NYC
- Phone: +16232634638 (voice/text)
- Bluesky: https://bsky.app/profile/oceansofnyc.bsky.social
- Note: "Fisker Ocean Sightings Bot - Text photos of Fisker Oceans in NYC to help track these unique EVs!"

## How to Use

### Option 1: Generate QR Code

Use any QR code generator:
- https://www.qr-code-generator.com/ (Upload File option)
- https://qr.io/
- Command line: `qrencode -t PNG -o oceansofnyc-qr.png < oceansofnyc.vcf`

### Option 2: Direct Download Link

Host the .vcf file on your website and share the link:
```
https://oceansofnyc.com/contact.vcf
```

### Option 3: Email/Share

Simply attach the .vcf file to emails or messages

## Testing

You can test the vCard by:
1. Opening the file on your phone
2. It should prompt to add to contacts
3. Verify all fields imported correctly

## Recommendations

- **For print materials**: Use the full version with logo for a branded experience
- **For quick sharing**: Use the simple version for faster scanning
- **For web**: Offer both as download options
