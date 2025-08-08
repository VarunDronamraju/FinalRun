import os
import mimetypes
import hashlib
from pathlib import Path
from typing import List, Optional
import logging
import re

logger = logging.getLogger(__name__)

def generate_file_id() -> str:
    """Generate unique file ID"""
    import uuid
    return str(uuid.uuid4())

def get_file_type(filename: str) -> str:
    """Get file type from filename"""
    mime_type, _ = mimetypes.guess_type(filename)
    if mime_type:
        if "pdf" in mime_type:
            return "pdf"
        elif "word" in mime_type or "document" in mime_type:
            return "docx"
        elif "text" in mime_type:
            return "txt"
    
    # Fallback to extension
    ext = Path(filename).suffix.lower()
    if ext == ".pdf":
        return "pdf"
    elif ext in [".docx", ".doc"]:
        return "docx"
    elif ext in [".txt", ".md"]:
        return "txt"
    else:
        return "unknown"

def validate_file_size(file_size: int, max_size_mb: int = 50) -> bool:
    """Validate file size"""
    max_size_bytes = max_size_mb * 1024 * 1024
    return file_size <= max_size_bytes

def sanitize_filename(filename: str) -> str:
    """Sanitize filename for safe storage"""
    # Remove path traversal attempts
    filename = os.path.basename(filename)
    # Remove dangerous characters
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    return filename

def create_upload_dir() -> Path:
    """Create upload directory if it doesn't exist"""
    upload_dir = Path("uploads")
    upload_dir.mkdir(exist_ok=True)
    return upload_dir

def save_uploaded_file(file_content: bytes, filename: str) -> str:
    """Save uploaded file and return file path"""
    upload_dir = create_upload_dir()
    safe_filename = sanitize_filename(filename)
    file_path = upload_dir / safe_filename
    
    # Add timestamp if file exists
    counter = 1
    original_path = file_path
    while file_path.exists():
        stem = original_path.stem
        suffix = original_path.suffix
        file_path = upload_dir / f"{stem}_{counter}{suffix}"
        counter += 1
    
    with open(file_path, "wb") as f:
        f.write(file_content)
    
    return str(file_path)

def get_file_hash(file_path: str) -> str:
    """Get MD5 hash of file"""
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def clean_text(text: str) -> str:
    """Clean text for processing"""
    # Remove excessive whitespace
    text = re.sub(r'\s+', ' ', text)
    # Remove special characters but keep punctuation
    text = re.sub(r'[^\w\s\.,!?;:()\-\'""]', ' ', text)
    # Remove multiple spaces
    text = re.sub(r' +', ' ', text)
    return text.strip()

def split_text_by_paragraphs(text: str) -> List[str]:
    """Split text into paragraphs"""
    paragraphs = text.split('\n\n')
    return [p.strip() for p in paragraphs if p.strip()]

def count_words(text: str) -> int:
    """Count words in text"""
    return len(text.split())

def validate_chunk_quality(chunk_text: str, min_length: int = 50) -> bool:
    """Validate if chunk has sufficient content"""
    if len(chunk_text.strip()) < min_length:
        return False
    if count_words(chunk_text) < 5:
        return False
    return True