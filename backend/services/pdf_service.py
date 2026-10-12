from pathlib import Path
from typing import Dict, Any, List, Tuple
from services.pdf_extractor import extract_from_pdf

def extract_textbook_from_pdf(pdf_path: Path, filename: str) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Extracts text, chapters, sections, embedded figures, tables, and chunks from a PDF file.
    Maintains full backward compatibility.
    """
    metadata, chunks, media_items = extract_from_pdf(pdf_path, filename)
    return metadata, chunks
