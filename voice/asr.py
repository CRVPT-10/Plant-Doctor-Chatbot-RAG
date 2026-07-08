import os
from typing import Tuple
from utils.config import config
from utils.logger import get_logger

logger = get_logger("asr")

class SpeechToTextManager:
    """
    Handles speech recognition, transcribing audio files to text 
    using local faster-whisper or standard Whisper fallback.
    """
    def __init__(self, model_size: str = None, device: str = None):
        self.model_size = model_size or config.get("voice.asr.model_size", "base")
        self.device = device or config.get("voice.asr.device", "cpu")
        self.compute_type = config.get("voice.asr.compute_type", "int8")
        self.models_dir = config.get_absolute_path("paths.models_dir")
        
        self.model = None
        self.enabled = True
        
        # Ensure models directory exists
        whisper_cache_dir = os.path.join(self.models_dir, "whisper")
        os.makedirs(whisper_cache_dir, exist_ok=True)
        
        logger.info(f"Initializing WhisperModel '{self.model_size}' on '{self.device}'...")
        try:
            from faster_whisper import WhisperModel
            self.model = WhisperModel(
                self.model_size,
                device=self.device,
                compute_type=self.compute_type,
                download_root=whisper_cache_dir
            )
            logger.info("WhisperModel initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to load faster-whisper model: {e}. STT features will be unavailable or mocked.")
            self.enabled = False

    def transcribe(self, audio_path: str) -> Tuple[str, str]:
        """
        Transcribes the audio file and returns a tuple (transcribed_text, detected_language).
        """
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
            
        if not self.enabled or not self.model:
            logger.warning("ASR is disabled or not loaded. Returning fallback text.")
            return "Speech recognition is currently offline. Please type your query.", "en"
            
        logger.info(f"Transcribing audio file: {audio_path}")
        try:
            # Transcribe audio file. beam_size=5 is standard for good accuracy
            segments, info = self.model.transcribe(audio_path, beam_size=5)
            
            # Join segments to reconstruct the full text
            text_segments = []
            for segment in segments:
                text_segments.append(segment.text)
                
            full_text = " ".join(text_segments).strip()
            detected_lang = info.language # e.g. 'en', 'hi', 'te', 'ta'
            
            logger.info(f"Transcribed Text: '{full_text}' | Detected Language: '{detected_lang}' (Prob: {info.language_probability:.2f})")
            return full_text, detected_lang
            
        except Exception as e:
            logger.error(f"Error during audio transcription: {e}")
            raise RuntimeError(f"Transcription error: {str(e)}")
