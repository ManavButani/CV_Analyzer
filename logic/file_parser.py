"""Utility functions for parsing PDF, DOCX, and text files"""
import os
import base64
from typing import Optional
import tempfile


def parse_text_file(content: str) -> str:
    """Parse plain text content"""
    return content.strip()


def parse_pdf_file(file_path: str) -> str:
    """Parse PDF file and extract text content"""
    try:
        import PyPDF2
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
            return text.strip()
    except ImportError:
        # Fallback: try pdfplumber
        try:
            import pdfplumber
            text = ""
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    text += page.extract_text() + "\n"
            return text.strip()
        except ImportError:
            raise ImportError(
                "PDF parsing requires either PyPDF2 or pdfplumber. "
                "Install with: pip install PyPDF2 or pip install pdfplumber"
            )


def parse_docx_file(file_path: str) -> str:
    """Parse DOCX file and extract text content"""
    try:
        from docx import Document
        doc = Document(file_path)
        text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
        return text.strip()
    except ImportError:
        raise ImportError(
            "DOCX parsing requires python-docx. Install with: pip install python-docx"
        )


def decode_base64_file(base64_content: str, file_format: str) -> str:
    """Decode base64 content and save to temporary file, return file path"""
    try:
        decoded_content = base64.b64decode(base64_content)
        # Create temporary file
        suffix = f".{file_format.lower()}"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
            tmp_file.write(decoded_content)
            return tmp_file.name
    except Exception as e:
        raise ValueError(f"Failed to decode base64 file: {str(e)}")


def extract_text_from_file(
    file_path: Optional[str] = None,
    base64_content: Optional[str] = None,
    file_format: str = "txt",
    text_content: Optional[str] = None
) -> str:
    """
    Extract text from file or text content.
    Supports PDF, DOCX, and plain text formats.
    """
    if text_content:
        return parse_text_file(text_content)
    
    if not file_path and not base64_content:
        raise ValueError("Either file_path, base64_content, or text_content must be provided")
    
    # Handle base64 content
    if base64_content:
        file_path = decode_base64_file(base64_content, file_format)
        should_delete = True
    else:
        should_delete = False
    
    try:
        file_format_lower = file_format.lower() if file_format else "txt"
        
        if file_format_lower == "pdf":
            text = parse_pdf_file(file_path)
        elif file_format_lower == "docx":
            text = parse_docx_file(file_path)
        elif file_format_lower == "txt":
            text = parse_text_file(open(file_path, 'r', encoding='utf-8').read())
        else:
            raise ValueError(f"Unsupported file format: {file_format}")
        
        return text
    finally:
        # Clean up temporary file if created from base64
        if should_delete and file_path and os.path.exists(file_path):
            try:
                os.unlink(file_path)
            except:
                pass
