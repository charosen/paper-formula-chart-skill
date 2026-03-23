#!/usr/bin/env python3
"""
Render PDF pages to high-resolution PNG images.
Usage: python render_pages.py <pdf_path> <output_dir> [zoom]
Default zoom: 3.0
"""
import sys
import fitz
import os

def render_pdf(pdf_path, output_dir, zoom=3.0):
    if not os.path.exists(pdf_path):
        print(f"Error: PDF not found: {pdf_path}")
        return

    os.makedirs(output_dir, exist_ok=True)
    doc = fitz.open(pdf_path)
    
    print(f"Pages: {len(doc)}, PDF size: {doc[0].rect.width}x{doc[0].rect.height}")
    print(f"Rendering at {zoom}x zoom...")
    
    for i in range(len(doc)):
        page = doc[i]
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat)
        out_path = os.path.join(output_dir, f"page_{i+1:02d}.png")
        pix.save(out_path)
        print(f"  Saved: {out_path} ({pix.width}x{pix.height})")
    
    doc.close()
    print(f"\nDone! {len(doc)} pages rendered.")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python render_pages.py <pdf_path> <output_dir> [zoom]")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    output_dir = sys.argv[2]
    zoom = float(sys.argv[3]) if len(sys.argv) > 3 else 3.0
    
    render_pdf(pdf_path, output_dir, zoom)
