# Tweet Box Assets

This directory should contain PNG images for tweet boxes used in Instagram Reel video generation.

## Required Files

You need to create **3 PNG images** with the following names:

1. `tweet_1liner.png` - For tweets with 1 line of text
2. `tweet_2liner.png` - For tweets with 2 lines of text
3. `tweet_3liner.png` - For tweets with 3 lines of text

## Specifications

### Dimensions
- Video resolution: **2160x3840** (9:16 vertical, 4K)
- Recommended box width: **1900-1950 pixels** (90% of video width)
- Box height: Variable based on text lines
  - 1-liner: ~400-500 pixels
  - 2-liner: ~500-650 pixels
  - 3-liner: ~650-800 pixels

### Design Guidelines

**Format:**
- File type: PNG with transparency
- Color mode: RGBA
- DPI: 72 (screen resolution)

**Visual Style:**
- Background: White or light gray (#FFFFFF or #F7F9FA)
- Rounded corners: 20-30 pixel radius
- Shadow: Subtle drop shadow (optional)
  - Offset: 0px, 4px
  - Blur: 12px
  - Color: rgba(0, 0, 0, 0.1)
- Border: None or 1px subtle border (#E1E8ED)

**Layout:**
- Padding: 40-60 pixels on all sides
- Text area: Center-aligned space for tweet text
- Account info area: Top section for @handle and profile pic (optional)
- Engagement metrics area: Bottom section for likes/retweets (optional)

## Design Inspiration

Use Twitter/X's actual tweet UI as reference:
- Clean, minimal design
- High contrast for readability
- Professional appearance
- Mobile-friendly proportions

## Creation Tools

### Recommended Options

**Figma** (Recommended)
- Professional design tool
- Easy collaboration
- Export to PNG
- https://figma.com

**Photoshop**
- Industry standard
- Advanced effects
- Artboard tool for multiple sizes

**GIMP** (Free)
- Open source alternative
- All necessary features
- https://www.gimp.org

**Canva**
- Online design tool
- Template library
- Easy to use
- https://canva.com

## Quick Start Template

### Basic Tweet Box Recipe

1. **Create artboard:** 1900x500px (for 1-liner)
2. **Add background:** White rectangle with 25px rounded corners
3. **Add shadow:** Soft drop shadow (0, 4, 12, 0.1)
4. **Add padding:** 50px margins on all sides
5. **Export:** PNG with transparency at 2x or @2x

### Layout Structure

```
┌─────────────────────────────────────────┐
│  Padding (50px)                         │
│  ┌───────────────────────────────────┐  │
│  │ @username · 2h                    │  │ ← Header (optional)
│  │                                   │  │
│  │ Tweet text goes here              │  │ ← Main text area
│  │ on one or more lines              │  │
│  │                                   │  │
│  │ ❤️ 1.2K  🔄 345  💬 89           │  │ ← Engagement (optional)
│  └───────────────────────────────────┘  │
│  Padding (50px)                         │
└─────────────────────────────────────────┘
```

## Tips

- Keep design minimal to match Twitter aesthetic
- Use system fonts or Twitter's standard fonts
- Test readability at mobile sizes
- Leave extra vertical space for dynamic text
- Export at high resolution for 4K video
- Save your design files for future edits

## Testing

After creating your PNG files:

1. Place them in this directory
2. Run validation: `python setup_assets.py`
3. Generate test video to verify appearance
4. Adjust dimensions/styling as needed

## Need Help?

Run the setup script for more detailed instructions:
```bash
python setup_assets.py
```
