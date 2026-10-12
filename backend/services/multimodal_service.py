import os
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
from services.pdf_extractor import extract_from_pdf
from services.presentation_extractor import extract_from_presentation
from services.video_extractor import extract_from_video

SUPPORTED_EXTENSIONS = {
    ".pdf": "pdf",
    ".ppt": "presentation",
    ".pptx": "presentation",
    ".mp4": "video",
}

def detect_file_type(filename: str) -> str:
    """
    Detects the multimodal source type from filename extension.
    Returns: 'pdf', 'presentation', 'video', or raises ValueError.
    """
    ext = Path(filename).suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"Unsupported file format '{ext}'. Supported formats are: PDF (.pdf), PowerPoint (.ppt, .pptx), and MP4 Video (.mp4)."
        )
    return SUPPORTED_EXTENSIONS[ext]

def process_multimodal_file(file_path: Path, filename: str, custom_id: Optional[str] = None) -> Tuple[Dict[str, Any], List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Master multimodal extraction pipeline:
    1. Detects file type
    2. Dispatches to specialized extractor
    3. Extracts actual text, images, tables, speech transcripts, and keyframes
    4. Preserves exact source location provenance (page / slide / timestamp)
    5. Normalizes into unified content structure
    """
    source_type = detect_file_type(filename)

    if not file_path.exists():
        raise FileNotFoundError(f"Uploaded file does not exist: {file_path}")

    file_size = file_path.stat().st_size
    if file_size == 0:
        raise ValueError("The uploaded file is empty (0 bytes). Please upload a valid file.")

    try:
        if source_type == "pdf":
            return extract_from_pdf(file_path, filename, custom_id=custom_id)
        elif source_type == "presentation":
            return extract_from_presentation(file_path, filename, custom_id=custom_id)
        elif source_type == "video":
            return extract_from_video(file_path, filename, custom_id=custom_id)
        else:
            raise ValueError(f"Unknown source type: {source_type}")
    except Exception as e:
        # Provide clean, human-readable error messages
        err_msg = str(e)
        if "Unable to" in err_msg or "Unsupported" in err_msg or "empty" in err_msg:
            raise ValueError(err_msg)
        raise ValueError(f"Unable to extract content from this file ({filename}): {err_msg}. Please check that the file is valid.")

def unify_course_materials(course_id: str, course_title: str, materials: List[Dict[str, Any]]) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Combines multiple multimodal materials (PDF, PPT, MP4) belonging to the same course
    into a unified course knowledge base while retaining individual source locations.
    """
    all_chunks = []
    all_media = []
    unified_chapters = []
    total_pages = 0
    total_slides = 0
    total_duration = 0.0

    for mat_idx, mat in enumerate(materials):
        m_meta = mat["metadata"]
        m_chunks = mat["chunks"]
        m_media = mat.get("media_items", [])

        s_type = m_meta.get("source_type", "pdf")
        if s_type == "pdf":
            total_pages += m_meta.get("total_pages", 0)
        elif s_type == "presentation":
            total_slides += m_meta.get("total_slides", 0)
        elif s_type == "video":
            total_duration += m_meta.get("duration_seconds", 0.0)

        # Prefix chapters to avoid collision
        for ch in m_meta.get("chapters", []):
            unified_chapters.append({
                **ch,
                "id": f"{m_meta['id']}_{ch['id']}",
                "title": f"[{s_type.upper()}] {ch['title']}"
            })

        for chunk in m_chunks:
            all_chunks.append({
                **chunk,
                "id": f"{course_id}_{chunk['id']}",
                "textbook_id": course_id,
                "material_id": m_meta["id"],
                "course_id": course_id
            })

        all_media.extend(m_media)

    unified_metadata = {
        "id": course_id,
        "title": course_title,
        "filename": f"course_unified_{course_id}",
        "source_type": "multimodal_course",
        "total_pages": total_pages,
        "total_slides": total_slides,
        "duration_seconds": total_duration,
        "file_size_bytes": sum(m["metadata"].get("file_size_bytes", 0) for m in materials),
        "extracted_images_count": sum(m["metadata"].get("extracted_images_count", 0) for m in materials),
        "extracted_transcripts_count": sum(m["metadata"].get("extracted_transcripts_count", 0) for m in materials),
        "extracted_tables_count": sum(m["metadata"].get("extracted_tables_count", 0) for m in materials),
        "media_items": all_media,
        "chapters": unified_chapters,
        "created_at": "2026-10-07T12:00:00"
    }

    return unified_metadata, all_chunks
