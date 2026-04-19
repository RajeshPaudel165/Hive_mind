"""MCP PDF Generation Server for Hive Brain"""
from __future__ import annotations

import base64
import json
import os
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas


load_dotenv()

PDF_STORAGE_PATH = Path(os.getenv("MCP_PDF_STORAGE_PATH", "data/pdfs"))
PDF_MAX_SIZE_MB = float(os.getenv("MCP_PDF_MAX_SIZE_MB", "10"))
PDF_MAX_SIZE_BYTES = int(PDF_MAX_SIZE_MB * 1024 * 1024)

# Create storage directory
PDF_STORAGE_PATH.mkdir(parents=True, exist_ok=True)


def generate_pdf_from_notes(title: str, content: str) -> dict[str, Any]:
    """Generate PDF from text content"""
    try:
        pdf_buffer = BytesIO()
        pdf_canvas = canvas.Canvas(pdf_buffer, pagesize=letter)
        
        width, height = letter
        
        # Add title
        pdf_canvas.setFont("Helvetica-Bold", 16)
        pdf_canvas.drawString(50, height - 50, title)
        
        # Add timestamp
        pdf_canvas.setFont("Helvetica", 9)
        timestamp = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
        pdf_canvas.drawString(50, height - 70, f"Generated: {timestamp}")
        
        # Add horizontal line
        pdf_canvas.line(50, height - 80, width - 50, height - 80)
        
        # Add content with word wrapping
        pdf_canvas.setFont("Helvetica", 10)
        y = height - 100
        x = 50
        max_width = width - 100
        
        # Split content into lines and wrap
        for line in content.split("\n"):
            if not line.strip():
                y -= 15
                continue
                
            words = line.split(" ")
            current_line = ""
            
            for word in words:
                test_line = f"{current_line} {word}".strip()
                if pdf_canvas.stringWidth(test_line, "Helvetica", 10) < max_width:
                    current_line = test_line
                else:
                    if current_line:
                        if y < 50:
                            pdf_canvas.showPage()
                            pdf_canvas.setFont("Helvetica", 10)
                            y = height - 50
                        pdf_canvas.drawString(x, y, current_line)
                        y -= 12
                    current_line = word
            
            if current_line:
                if y < 50:
                    pdf_canvas.showPage()
                    pdf_canvas.setFont("Helvetica", 10)
                    y = height - 50
                pdf_canvas.drawString(x, y, current_line)
                y -= 12
        
        pdf_canvas.save()
        pdf_buffer.seek(0)
        pdf_data = pdf_buffer.read()
        
        # Check size
        if len(pdf_data) > PDF_MAX_SIZE_BYTES:
            return {
                "success": False,
                "error": f"PDF exceeds max size of {PDF_MAX_SIZE_MB}MB"
            }
        
        # Save to disk
        filename = f"{title.replace(' ', '_')}_{datetime.now(UTC).timestamp()}.pdf"
        file_path = PDF_STORAGE_PATH / filename
        file_path.write_bytes(pdf_data)
        
        return {
            "success": True,
            "filename": filename,
            "filepath": str(file_path),
            "size_bytes": len(pdf_data),
            "pdf_base64": base64.b64encode(pdf_data).decode()
        }
    
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def generate_pdf_from_memories(
    pairing_code: str,
    room: str,
    memories: list[dict[str, str]]
) -> dict[str, Any]:
    """Generate PDF from MemPalace memories"""
    try:
        # Format memories into readable content
        content = f"Room: {room}\n"
        content += f"Pairing Code: {pairing_code}\n"
        content += "=" * 50 + "\n\n"
        
        for idx, memory in enumerate(memories, 1):
            timestamp = memory.get("created_at", "Unknown")
            memory_content = memory.get("content", "")
            content += f"[{idx}] {timestamp}\n"
            content += f"{memory_content}\n"
            content += "-" * 40 + "\n\n"
        
        title = f"{room}_Notes_{datetime.now(UTC).strftime('%Y%m%d')}"
        return generate_pdf_from_notes(title, content)
    
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def get_stored_pdfs() -> dict[str, Any]:
    """List all stored PDFs"""
    try:
        pdfs = list(PDF_STORAGE_PATH.glob("*.pdf"))
        return {
            "success": True,
            "count": len(pdfs),
            "pdfs": [p.name for p in pdfs]
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def retrieve_pdf(filename: str) -> dict[str, Any]:
    """Retrieve a stored PDF by filename"""
    try:
        file_path = PDF_STORAGE_PATH / filename
        
        # Security: prevent directory traversal
        if not file_path.resolve().is_relative_to(PDF_STORAGE_PATH.resolve()):
            return {
                "success": False,
                "error": "Invalid filename"
            }
        
        if not file_path.exists():
            return {
                "success": False,
                "error": f"PDF not found: {filename}"
            }
        
        pdf_data = file_path.read_bytes()
        return {
            "success": True,
            "filename": filename,
            "size_bytes": len(pdf_data),
            "pdf_base64": base64.b64encode(pdf_data).decode()
        }
    
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


if __name__ == "__main__":
    # Test the PDF generator
    test_content = """
    Introduction to Fourier Analysis
    
    Fourier analysis is a tool for breaking apart periodic functions or periodic signals 
    into an infinite or finite sum of simple oscillating functions, namely sines and cosines 
    (or, from another point of view, exponential functions).
    
    Key Concepts:
    - Periodic Functions: Functions that repeat at regular intervals
    - Fourier Series: Representation of periodic functions as sums of sine and cosine terms
    - Fourier Transform: Extension to non-periodic functions
    
    Applications:
    - Signal Processing
    - Image Analysis
    - Data Compression
    - Solving Differential Equations
    """
    
    result = generate_pdf_from_notes("Fourier_Analysis_Notes", test_content)
    print(json.dumps(result, indent=2))
