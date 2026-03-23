#!/usr/bin/env python3
"""
Extract text blocks from PDF pages using PyMuPDF.
Outputs one JSON file per page with text block positions.
Usage: python extract_text_blocks.py <pdf_path> <output_meta_dir>
"""
import sys
import fitz
import json
import os

def extract_text_blocks(pdf_path, output_dir):
    if not os.path.exists(pdf_path):
        print(f"Error: PDF not found: {pdf_path}")
        return

    os.makedirs(output_dir, exist_ok=True)
    doc = fitz.open(pdf_path)
    
    print(f"PDF size: {doc[0].rect.width}x{doc[0].rect.height}")
    
    for i in range(len(doc)):
        page = doc[i]
        pw, ph = page.rect.width, page.rect.height
        blocks = page.get_text("dict")["blocks"]
        
        text_blocks = []
        for b in blocks:
            if b["type"] == 0:  # text block
                bb = b["bbox"]
                lines = b.get("lines", [])
                words = []
                for line in lines[:2]:  # first 2 lines as label
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
            "page": i + 1,
            "pdf_size": {"w": int(pw), "h": int(ph)},
            "screenshot_size": {"w": int(pw * 3), "h": int(ph * 3)},
            "text_blocks": text_blocks
        }
        
        out_path = os.path.join(output_dir, f"page_{i+1:02d}_text.json")
        with open(out_path, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"  Page {i+1}: {len(text_blocks)} text blocks")

    doc.close()
    print(f"\nDone! Text blocks saved to {output_dir}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python extract_text_blocks.py <pdf_path> <output_meta_dir>")
        sys.exit(1)
    
    extract_text_blocks(sys.argv[1], sys.argv[2])
