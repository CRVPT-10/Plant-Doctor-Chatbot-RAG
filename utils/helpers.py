import os
import hashlib

def get_text_hash(text: str) -> str:
    """Returns MD5 hash of text."""
    return hashlib.md5(text.encode("utf-8", errors="ignore")).hexdigest()

def detect_language(text: str) -> str:
    """
    Heuristic-based language detection for English, Hindi, Telugu, and Tamil.
    Falls back to 'en' if not matched.
    """
    if not text:
        return "en"
    
    # Take a sample of text to detect language to avoid scanning very large docs
    sample = text[:5000]
    
    devanagari_count = 0
    telugu_count = 0
    tamil_count = 0
    total_chars = 0
    
    for char in sample:
        code = ord(char)
        total_chars += 1
        if 0x0900 <= code <= 0x097F:
            devanagari_count += 1
        elif 0x0C00 <= code <= 0x0C7F:
            telugu_count += 1
        elif 0x0B80 <= code <= 0x0BFF:
            tamil_count += 1
            
    if total_chars == 0:
        return "en"
        
    # Check if foreign characters represent a significant portion (> 5%)
    threshold = 0.05
    if (devanagari_count / total_chars) > threshold:
        return "hi"
    elif (telugu_count / total_chars) > threshold:
        return "te"
    elif (tamil_count / total_chars) > threshold:
        return "ta"
        
    return "en"
