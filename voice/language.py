from typing import Dict

# Supported languages list
SUPPORTED_LANGUAGES = {
    "en": "English",
    "hi": "Hindi",
    "te": "Telugu",
    "ta": "Tamil"
}

# Reverse mapping
LANGUAGE_TO_CODE = {v: k for k, v in SUPPORTED_LANGUAGES.items()}

# Default voice mapping for Edge TTS Neural voices
EDGE_VOICES = {
    "en": "en-US-GuyNeural",
    "hi": "hi-IN-MadhurNeural",
    "te": "te-IN-MohanNeural",
    "ta": "ta-IN-ValluvarNeural"
}

def get_language_name(code: str) -> str:
    """Gets human readable language name from ISO 639-1 code."""
    return SUPPORTED_LANGUAGES.get(code.lower(), "English")

def get_language_code(name: str) -> str:
    """Gets language code from human readable language name."""
    return LANGUAGE_TO_CODE.get(name, "en")
