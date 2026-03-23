---
name: paper-formula-chart-skill
description: Extract figures, tables, and equations from academic papers (PDF) with precise coordinates. Use when asked to parse, analyze, or extract content from research papers — specifically: (1) identifying figures/charts/diagrams, (2) locating tables, (3) finding mathematical equations/formulas, (4) generating annotated page images with bounding boxes, (5) saving cropped element images with coordinate metadata in JSON. Triggered by requests like "extract figures from paper", "parse PDF layout", "analyze paper charts/tables", "scan paper formulas with coordinates".
---

# Paper Figure/Table/Equation Extraction

## Core Principle

**Use PyMuPDF text coordinates as anchors. Use vision model only for content description — never for coordinate estimation.**

Vision models (including MiniMax-M2.7-highspeed) have systematic y-coordinate errors when estimating PDF coordinates. Always use PyMuPDF's `get_text("words")` or `get_text("dict")["blocks"]` to get precise PDF point coordinates, then derive element boundaries from text positions.

## Coordinate System

| System | Origin | Units | Scale |
|--------|--------|-------|-------|
| PDF points | top-left | 0–612 × 0–792 (A4 portrait) | 1 pt = 1/72 inch |
| Screenshot (3× zoom) | top-left | 0–1836 × 0–2376 | 1 pt = 3 px |
| Normalized | top-left | 0–1 | — |

Conversions: `px3_x = pdf_x × 3`, `px3_y = pdf_y × 3`

## Pipeline

### 1. Render PDF pages

```python
import fitz, os

pdf_path = "paper.pdf"
img_dir = "output/image"
os.makedirs(img_dir, exist_ok=True)

doc = fitz.open(pdf_path)
for i in range(len(doc)):
    page = doc[i]
    mat = fitz.Matrix(3.0, 3.0)  # 3× zoom for precision
    pix = page.get_pixmap(matrix=mat)
    pix.save(f"{img_dir}/page_{i+1:02d}.png")
doc.close()
```

### 2. Extract text blocks (anchor data)

```python
import fitz, json, os

pdf_path = "paper.pdf"
meta_dir = "output/meta"
os.makedirs(meta_dir, exist_ok=True)

doc = fitz.open(pdf_path)
for i in range(len(doc)):
    page = doc[i]
    pw, ph = page.rect.width, page.rect.height  # e.g. 612, 792

    blocks = page.get_text("dict")["blocks"]
    text_blocks = []
    for b in blocks:
        if b["type"] == 0:  # text block
            bb = b["bbox"]
            lines = b.get("lines", [])
            words = []
            for line in lines[:2]:
                for span in line.get("spans", [])[:5]:
                    t = span["text"].strip()
                    if t:
                        words.append(t)
            label = " ".join(words)[:80]
            text_blocks.append({
                "label": label,
                "x0": round(bb[0], 1),
                "y0": round(bb[1], 1),
                "x1": round(bb[2], 1),
                "y1": round(bb[3], 1)
            })

    data = {
        "page": i+1,
        "pdf_size": {"w": pw, "h": ph},
        "screenshot_size": {"w": pw*3, "h": ph*3},
        "text_blocks": text_blocks
    }
    with open(f"{meta_dir}/page_{i+1:02d}_text.json", "w") as f:
        json.dump(data, f, indent=2)
doc.close()
```

### 3. Analyze and determine element boundaries

For each page, analyze text blocks to find:
- **Figure/Table captions**: look for `"Figure N:"` or `"Table N:"` in labels
- **Equation numbers**: look for patterns like `"(1)"`, `"(2)"` in text blocks
- **Element extents**: use the surrounding text positions to determine top/bottom boundaries

**Rules for boundaries:**
- Top boundary (y0): first content pixel or text above the element
- Bottom boundary (y1): caption end or text below the element
- Do NOT include surrounding paragraph text in the crop
- Inline formulas (within running text) → **skip**
- Block equations (displayed, with number) → **include**

### 4. Generate output files

For each element, save:
1. `page_grounded_XX.png` — full page with colored bounding boxes drawn
2. `pXX_type_N_label.png` — cropped element (no boxes)
3. `meta/page_XX.json` — coordinates

```python
import json, os
from PIL import Image, ImageDraw

page_num = 1
elements = [
    {
        "type": "figure",  # or "table", "equation", "algorithm"
        "label": "Figure 1: Comparison chart",
        "pdf_coords": {"x0": 108, "y0": 510, "x1": 504, "y1": 692}
    }
]

# Convert to all coordinate systems
for el in elements:
    pdf = el["pdf_coords"]
    el["norm_coords"] = {
        "x0": round(pdf["x0"]/612, 4), "y0": round(pdf["y0"]/792, 4),
        "x1": round(pdf["x1"]/612, 4), "y1": round(pdf["y1"]/792, 4)
    }
    el["px3_coords"] = {
        "x0": int(pdf["x0"]*3), "y0": int(pdf["y0"]*3),
        "x1": int(pdf["x1"]*3), "y1": int(pdf["y1"]*3)
    }

# Save meta
meta = {"page": page_num, "elements": elements}
with open(f"output/meta/page_{page_num:02d}.json", "w") as f:
    json.dump(meta, f, indent=2)

# Draw grounded page
img = Image.open(f"output/image/page_{page_num:02d}.png")
draw = ImageDraw.Draw(img)
colors = {"figure": "red", "table": "blue", "equation": "green", "algorithm": "yellow"}
for el in elements:
    px = el["px3_coords"]
    draw.rectangle([px["x0"],px["y0"],px["x1"],px["y1"]],
                   outline=colors.get(el["type"],"white"), width=8)
img.save(f"output/image/page_grounded_{page_num:02d}.png")

# Save crops (no boxes)
img_orig = Image.open(f"output/image/page_{page_num:02d}.png")
for i, el in enumerate(elements):
    px = el["px3_coords"]
    crop = img_orig.crop((px["x0"],px["y0"],px["x1"],px["y1"]))
    safe_label = el["label"].replace(" ", "_").replace(":", "_")[:50]
    fname = f"p{page_num:02d}_{el['type']}_{i+1}_{safe_label}.png"
    crop.save(f"output/image/{fname}")
```

### 5. User verification loop

**Process one page at a time. Report each element before cropping.**

For each page, present:
```
| Element | Type | PDF coords | Normalized coords | Crop size |
|---------|------|------------|-------------------|------------|
| Figure 1: ... | figure | x=[108,504] y=[510,692] | x=[0.177,0.824] y=[0.644,0.874] | 1188×546 |
```

**After user feedback:**
- "上方截取不全" → decrease y0 (raise top edge)
- "下方截取不全" → increase y1 (lower bottom edge)
- "截进了正文" → adjust y0 up or y1 down to exclude paragraph text

## Common Issues & Fixes

| Issue | Cause | Fix |
|-------|-------|-----|
| Vision model y-coords wrong by ~24% | y-axis estimation unreliable | Always use PyMuPDF text coords |
| Equation crop includes paragraph above | y0 too high | Lower y0 to just above formula line |
| Table/Figure crop cuts off caption | y1 too low | Extend y1 to include caption |
| Multiple equations in one block | misidentified boundaries | Split into separate elements per equation |

## Directory Structure

```
output/
├── image/
│   ├── page_01.png              # Full page screenshot (3× zoom)
│   ├── page_grounded_01.png     # Annotated with colored boxes
│   ├── p01_figure_1_Figure_1.png
│   ├── p01_table_1_Table_1.png
│   └── p01_equation_1_Eq1.png
├── meta/
│   ├── page_01_text.json        # Raw PyMuPDF text blocks
│   └── page_01.json             # Analyzed element coordinates
```

## Key Pitfalls to Avoid

1. **Do not trust vision model coordinates** — vision models systematically misjudge y-axis positions in PDF coordinate space. Always use PyMuPDF text positions as anchors.
2. **Do not process all pages before verification** — process one page, show results, get user confirmation, then continue.
3. **Do not include inline formulas** — only crop block/display equations that have equation numbers.
4. **Always add padding** — when in doubt, extend boundaries slightly to avoid cutting off content.
5. **Verify each page with the user** — the user catches what the model misses.

## References

- Full methodology: [references/methodology.md](references/methodology.md)
- Coordinate system reference: [references/coordinate_system.md](references/coordinate_system.md)
- PyMuPDF script examples: [scripts/](scripts/)
