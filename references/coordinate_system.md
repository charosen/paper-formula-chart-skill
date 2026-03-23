# Coordinate System Reference

## PDF Coordinate System

**Origin:** Top-left corner of the page
**Y-axis:** Increases downward (toward bottom of page)
**Units:** PDF points (1 point = 1/72 inch)

Standard academic paper (A4 portrait): 612 × 792 PDF points

## Screenshot Coordinate System

When rendering with PyMuPDF at zoom factor Z:
- screenshot_width = PDF_width × Z
- screenshot_height = PDF_height × Z

**3× zoom (recommended):**
- 612 × 3 = 1836 pixels wide
- 792 × 3 = 2376 pixels tall

**Conversion:** `screenshot_pixel = PDF_point × Z`

## Normalized Coordinate System

For storing platform-independent coordinates:
- `norm_x = PDF_x / PDF_page_width`
- `norm_y = PDF_y / PDF_page_height`

Range: [0.0, 1.0] for both axes

## Conversion Table

| PDF Points (612×792) | Screenshot 3× | Normalized |
|---------------------|---------------|------------|
| x: 108 | x: 324 | x: 0.177 |
| x: 504 | x: 1512 | x: 0.824 |
| y: 510 | y: 1530 | y: 0.644 |
| y: 692 | y: 2076 | y: 0.874 |

## PyMuPDF Text Extraction

### Block-Level Extraction
```python
blocks = page.get_text("dict")["blocks"]
for b in blocks:
    if b["type"] == 0:  # text block
        bb = b["bbox"]  # [x0, y0, x1, y1] in PDF points
```

### Word-Level Extraction (for fine-grained analysis)
```python
words = page.get_text("words")
for w in words:
    # w = [x0, y0, x1, y1, word_text, block_no, line_no, word_no]
    print(f"y={w[1]:.1f}: '{w[4]}'")
```

### Drawing Paths (for chart/figure areas)
```python
paths = page.get_drawings()
for p in paths:
    if p.get('rect'):
        print(f"Path bbox: {p['rect']}")  # [x0, y0, x1, y1]
```

## Common Paper Layouts

### Single Column (full-width figures/tables)
- Left margin: ~108
- Right margin: ~504
- Full width: x=[108, 504]

### Two-Column Layout
- Left column: x=[108, ~306]
- Right column: x=[~306, 504]
- Gap: ~2-3mm at center

### Algorithm Boxes
Often occupy full width with visible border, title at top.

## Coordinate Conversion Formula

```python
# PDF to 3× screenshot pixels
px3_x0 = int(pdf_x0 * 3)
px3_y0 = int(pdf_y0 * 3)
px3_x1 = int(pdf_x1 * 3)
px3_y1 = int(pdf_y1 * 3)

# PDF to normalized
norm_x0 = round(pdf_x0 / 612, 4)
norm_y0 = round(pdf_y0 / 792, 4)
norm_x1 = round(pdf_x1 / 612, 4)
norm_y1 = round(pdf_y1 / 792, 4)
```

## JSON Output Format

```json
{
  "page": 1,
  "elements": [
    {
      "type": "figure",
      "label": "Figure 1: Description",
      "pdf_coords": {"x0": 108, "y0": 510, "x1": 504, "y1": 692},
      "norm_coords": {"x0": 0.1765, "y0": 0.6439, "x1": 0.8235, "y1": 0.8737},
      "px3_coords": {"x0": 324, "y0": 1530, "x1": 1512, "y1": 2076}
    }
  ]
}
```
