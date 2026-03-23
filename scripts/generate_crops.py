#!/usr/bin/env python3
"""
Generate grounded page images and cropped element images with coordinate metadata.

Usage:
  python generate_crops.py <page_num> <elements_json> <img_dir> <meta_dir>

elements_json format:
  A JSON string or file path containing list of elements:
  [
    {
      "type": "figure",  # figure | table | equation | algorithm
      "label": "Figure 1: Description",
      "pdf_coords": {"x0": 108, "y0": 510, "x1": 504, "y1": 692}
    }
  ]

Example:
  python generate_crops.py 1 '[{"type":"figure","label":"Fig1","pdf_coords":{"x0":108,"y0":510,"x1":504,"y1":692}}]' ./image ./meta
"""
import sys
import json
import os
from PIL import Image, ImageDraw

COLOR_MAP = {
    "figure": "red",
    "table": "blue",
    "equation": "green",
    "algorithm": "yellow"
}

def convert_coords(el, pdf_w=612, pdf_h=792, zoom=3):
    """Convert PDF coords to norm and px3."""
    pdf = el["pdf_coords"]
    el["norm_coords"] = {
        "x0": round(pdf["x0"] / pdf_w, 4),
        "y0": round(pdf["y0"] / pdf_h, 4),
        "x1": round(pdf["x1"] / pdf_w, 4),
        "y1": round(pdf["y1"] / pdf_h, 4)
    }
    el["px3_coords"] = {
        "x0": int(pdf["x0"] * zoom),
        "y0": int(pdf["y0"] * zoom),
        "x1": int(pdf["x1"] * zoom),
        "y1": int(pdf["y1"] * zoom)
    }
    return el

def generate_crops(page_num, elements, img_dir, meta_dir, pdf_w=612, pdf_h=792, zoom=3):
    # Convert all coordinates
    for el in elements:
        convert_coords(el, pdf_w, pdf_h, zoom)

    # Save meta JSON
    meta = {"page": page_num, "elements": elements}
    os.makedirs(meta_dir, exist_ok=True)
    meta_path = os.path.join(meta_dir, f"page_{page_num:02d}.json")
    with open(meta_path, "w") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)
    print(f"  Meta: {meta_path}")

    # Load page image
    page_path = os.path.join(img_dir, f"page_{page_num:02d}.png")
    if not os.path.exists(page_path):
        print(f"  Error: page image not found: {page_path}")
        return

    img = Image.open(page_path)
    
    # Draw grounded page with colored boxes
    img_gr = img.copy()
    draw = ImageDraw.Draw(img_gr)
    for el in elements:
        px = el["px3_coords"]
        color = COLOR_MAP.get(el["type"], "white")
        draw.rectangle([px["x0"], px["y0"], px["x1"], px["y1"]],
                       outline=color, width=8)
    gr_path = os.path.join(img_dir, f"page_grounded_{page_num:02d}.png")
    img_gr.save(gr_path)
    print(f"  Grounded: {gr_path}")

    # Save cropped elements (no boxes)
    os.makedirs(img_dir, exist_ok=True)
    for i, el in enumerate(elements):
        px = el["px3_coords"]
        crop = img.crop((px["x0"], px["y0"], px["x1"], px["y1"]))
        safe_label = (el["label"]
                      .replace(" ", "_")
                      .replace(":", "_")
                      .replace("(", "")
                      .replace(")", "")
                      .replace("[", "")
                      .replace("]", "")[:50])
        fname = f"p{page_num:02d}_{el['type']}_{i+1}_{safe_label}.png"
        crop.save(os.path.join(img_dir, fname))
        print(f"  Crop: {fname} ({crop.width}x{crop.height})")

    return meta

def main():
    if len(sys.argv) < 5:
        print("Usage: python generate_crops.py <page_num> <elements_json> <img_dir> <meta_dir>")
        print("  elements_json: JSON string or @filepath to JSON file")
        sys.exit(1)

    page_num = int(sys.argv[1])
    elements_arg = sys.argv[2]
    img_dir = sys.argv[3]
    meta_dir = sys.argv[4]

    # Load elements
    if elements_arg.startswith("@"):
        with open(elements_arg[1:]) as f:
            elements = json.load(f)
    else:
        elements = json.loads(elements_arg)

    print(f"\nPage {page_num}: {len(elements)} elements")
    generate_crops(page_num, elements, img_dir, meta_dir)

if __name__ == "__main__":
    main()
