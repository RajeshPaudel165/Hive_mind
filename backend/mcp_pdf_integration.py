"""OpenClaw MCP PDF Integration - Registers PDF tools with LLM"""
from __future__ import annotations

from mcp_pdf_server import (
    generate_pdf_from_notes,
    generate_pdf_from_memories,
    get_stored_pdfs,
    retrieve_pdf,
)


# PDF Tools for OpenClaw
PDF_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "create_pdf_from_notes",
            "description": "Generate a PDF document from notes or text content. Returns base64 PDF data that can be sent via Telegram.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "PDF title/filename (without .pdf extension)"
                    },
                    "content": {
                        "type": "string",
                        "description": "The text content to include in the PDF"
                    }
                },
                "required": ["title", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_pdf_from_memory",
            "description": "Generate a PDF from stored memories in MemPalace. Formats memories into a readable study document.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pairing_code": {
                        "type": "string",
                        "description": "User's pairing code (e.g., HIVE-1234)"
                    },
                    "room": {
                        "type": "string",
                        "description": "MemPalace room/project name (e.g., Fourier_Analysis)"
                    },
                    "memories": {
                        "type": "array",
                        "description": "List of memory objects from MemPalace",
                        "items": {
                            "type": "object",
                            "properties": {
                                "content": {"type": "string"},
                                "created_at": {"type": "string"}
                            }
                        }
                    }
                },
                "required": ["pairing_code", "room", "memories"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_pdfs",
            "description": "List all previously generated PDFs stored on the server",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "retrieve_pdf",
            "description": "Retrieve a previously generated PDF by filename",
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {
                        "type": "string",
                        "description": "PDF filename to retrieve"
                    }
                },
                "required": ["filename"]
            }
        }
    }
]


def execute_pdf_tool(tool_name: str, arguments: dict) -> dict:
    """Execute PDF MCP tool"""
    
    if tool_name == "create_pdf_from_notes":
        return generate_pdf_from_notes(
            title=arguments.get("title", "Document"),
            content=arguments.get("content", "")
        )
    
    elif tool_name == "create_pdf_from_memory":
        return generate_pdf_from_memories(
            pairing_code=arguments.get("pairing_code"),
            room=arguments.get("room"),
            memories=arguments.get("memories", [])
        )
    
    elif tool_name == "list_pdfs":
        return get_stored_pdfs()
    
    elif tool_name == "retrieve_pdf":
        return retrieve_pdf(arguments.get("filename"))
    
    else:
        return {
            "success": False,
            "error": f"Unknown tool: {tool_name}"
        }
