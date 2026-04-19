# MCP PDF Server Setup Guide

## Overview
The MCP PDF Server enables on-demand PDF generation when users request it through Telegram. The system:
1. User sends "Generate PDF" or similar request via Telegram
2. OpenClaw calls the PDF generation tool
3. PDF is created from memories or notes
4. PDF is sent back to user via Telegram

## Installation

### 1. Install Dependencies
```bash
cd backend
pip install -r requirements.txt
```

### 2. Configuration
The `.env` file includes MCP PDF settings:
```env
MCP_PDF_SERVER_URL=http://127.0.0.1:18790
MCP_PDF_ENABLED=true
MCP_PDF_STORAGE_PATH=data/pdfs
MCP_PDF_MAX_SIZE_MB=10
MCP_PDF_TIMEOUT_SECONDS=30
```

### 3. Create Storage Directory
```bash
mkdir -p data/pdfs
```

## Usage

### Option A: Direct PDF Generation from Notes
```python
from mcp_pdf_server import generate_pdf_from_notes

result = generate_pdf_from_notes(
    title="My Study Notes",
    content="Your notes here..."
)

if result["success"]:
    print(f"PDF created: {result['filename']}")
    pdf_b64 = result['pdf_base64']
    # Send pdf_b64 via Telegram
```

### Option B: Generate from MemPalace Memories
```python
from mcp_pdf_server import generate_pdf_from_memories
from mempalace_memory import get_memories

# Fetch memories from MemPalace
memories = get_memories(pairing_code="HIVE-1234", room="Fourier_Analysis")

result = generate_pdf_from_memories(
    pairing_code="HIVE-1234",
    room="Fourier_Analysis",
    memories=memories
)

pdf_b64 = result['pdf_base64']
```

## Integration with OpenClaw

The PDF tools are registered in `mcp_pdf_integration.py`:

```python
from mcp_pdf_integration import PDF_TOOLS, execute_pdf_tool

# Add PDF_TOOLS to OpenClaw request
payload = {
    "model": "openclaw",
    "messages": messages,
    "tools": PDF_TOOLS  # Include PDF tools
}

# When OpenClaw suggests a tool use:
if tool_call["function"]["name"].startswith("create_pdf"):
    result = execute_pdf_tool(tool_call["function"]["name"], arguments)
```

## Integration with Telegram Worker

Update `telegram_bot.py`:

```python
from mcp_pdf_integration import PDF_TOOLS, execute_pdf_tool
import base64

async def handle_pdf_request(message):
    # Call OpenClaw with PDF tools enabled
    response = await chat_completion(
        messages=[...],
        tools=PDF_TOOLS
    )
    
    if "tool_calls" in response:
        for tool_call in response["tool_calls"]:
            if "pdf" in tool_call["function"]["name"]:
                result = execute_pdf_tool(
                    tool_call["function"]["name"],
                    tool_call["function"]["arguments"]
                )
                
                if result.get("success"):
                    # Send PDF to Telegram
                    pdf_bytes = base64.b64decode(result["pdf_base64"])
                    await send_document_to_telegram(
                        chat_id=message.chat.id,
                        document=pdf_bytes,
                        filename=result["filename"]
                    )
```

## User Commands (via Telegram)

Examples that trigger PDF generation:
- "Generate PDF of my notes"
- "Export my Fourier Analysis memories to PDF"
- "Create a study guide PDF"
- "Make a PDF from today's learning"

## Troubleshooting

### PDF too large
Increase `MCP_PDF_MAX_SIZE_MB` in `.env`

### ReportLab import error
```bash
pip install --upgrade reportlab
```

### Storage issues
Check that `data/pdfs/` directory exists and is writable:
```bash
ls -la data/pdfs/
```

## Features

✅ Text-based PDF generation with word wrapping
✅ MemPalace memory export to organized PDFs
✅ Base64 encoding for easy Telegram transmission
✅ File size validation
✅ Timestamp and metadata inclusion
✅ Secure filename handling
