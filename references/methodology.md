# Methodology: PDF Figure/Table/Equation Extraction

## Overview

This skill extracts figures, tables, and equations from academic papers with precise bounding box coordinates. The key insight: **use PyMuPDF text positions as anchors, never trust vision model coordinate estimates.**

## The Vision Model Problem

When a vision model (even capable ones like MiniMax-M2.7-highspeed) is asked to estimate bounding box coordinates for elements in a PDF page, it systematically misjudges y-axis positions. Observed errors of 20-30% of page height are common.

Root cause: vision models process 2D images but have difficulty precisely mapping PDF coordinate space (top-left origin, y increases downward) to normalized 0-1 representations.

**Solution:** Use PyMuPDF to extract the actual text positions in PDF point coordinates. These are pixel-perfect anchors. Then determine element boundaries by analyzing where text labels (captions, equation numbers, axis labels) appear.

## Step-by-Step Methodology

### Step 1: Render PDF at High Resolution

Use 3× zoom when rendering PDF pages to images. This provides sufficient precision for accurate cropping.

```python
mat = fitz.Matrix(3.0, 3.0)
pix = page.get_pixmap(matrix=mat)
# Result: 612×3 = 1836px wide, 792×3 = 2376px tall
```

### Step 2: Extract Text Blocks

PyMuPDF's `get_text("dict")` returns text blocks with precise PDF point coordinates.

```python
blocks = page.get_text("dict")["blocks"]
for b in blocks:
    if b["type"] == 0:  # text block
        bb = b["bbox"]  # [x0, y0, x1, y1] in PDF points
```

### Step 3: Analyze Text Block Positions

Key insight: figure/table captions and equation numbers appear at predictable positions relative to the elements themselves.

**For Figures:**
1. Find "Figure N:" or "Fig. N:" in text blocks → this is the caption start
2. Look at y-axis labels (numbers like "35", "40" etc.) → these mark the chart top boundary
3. Look at x-axis labels → chart right boundary
4. The figure typically occupies the space between the caption and the next paragraph

**For Tables:**
1. Find "Table N:" → caption start
2. Look for column headers → top of table content
3. Look for horizontal rule or next section → bottom boundary

**For Equations:**
1. Find "(1)", "(2)" etc. → equation number, usually right-aligned
2. Look for the formula line itself (symbols like "=", "∇", "KL", "θ")
3. Equations span multiple lines when they have stacked fractions
4. Block equations have a number; inline formulas (within running text) should be skipped

### Step 4: Determine Boundaries

Use text block positions to determine precise boundaries:

**Figure example (Page 1 of MiniLLM paper):**
- "Figure 1:" caption text at y=637 (top of caption)
- y-axis labels "35", "40", "45", "50" at y=515-588
- "Average GPT4 Score" at y=518
- → Figure top boundary at y≈510 (above the y-axis labels)
- → Figure bottom boundary at y≈692 (end of caption)

**Equation example (Page 4 of MiniLLM paper):**
- "(4)" at y=285 (right margin)
- Formula line "ρ_t(θ) = α·p(...)" at y=285
- "where α controls..." paragraph at y=301
- → Equation 4: y0=280, y1=305 (captures just the formula line and number, not the following text)

### Step 5: Fine-Grained Text Extraction for Accuracy

When boundaries are unclear, use `get_text("words")` to get per-word positions:

```python
words = page.get_text("words")
for w in sorted(words, key=lambda x: (round(x[1]/5)*5, x[0])):
    if 120 <= w[1] <= 650:
        print(f"y={w[1]:.1f}: '{w[4]}' (x={w[0]:.1f}-{w[2]:.1f})")
```

This reveals the exact y-position of each text fragment, allowing precise boundary determination.

## Coordinate Conversion

All three coordinate systems are relative to top-left origin (y increases downward):

| System | PDF Page 612×792 | Screenshot 1836×2376 | Normalized |
|--------|-------------------|---------------------|-----------|
| Formula | x0_pdf | x0_pdf × 3 | x0_pdf / 612 |
| 1pt = 1/72" | y0_pdf | y0_pdf × 3 | y0_pdf / 792 |

Example: PDF coords [108, 504] × [510, 692]
- px3: [324, 1512] × [1530, 2076]
- normalized: [0.177, 0.824] × [0.644, 0.874]

## Visual Verification Loop

Always verify one page at a time with the user:
1. Generate page_grounded_XX.png with colored boxes
2. Show the user and wait for feedback
3. Adjust boundaries based on feedback
4. Continue to next page only after confirmation

**Common feedback patterns:**
- "上方截取不全" → decrease y0 (raise top edge)
- "下方截取不全" → increase y1 (lower bottom edge)  
- "把正文框进来了" → y0 too high or y1 too low → shrink from that side
