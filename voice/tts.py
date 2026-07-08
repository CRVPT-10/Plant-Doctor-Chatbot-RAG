import os
import asyncio
from gtts import gTTS
from utils.config import config
from utils.logger import get_logger
from utils.helpers import get_text_hash
from voice.language import EDGE_VOICES

logger = get_logger("tts")

class TextToSpeechManager:
    """
    Converts text to speech using Edge TTS or gTTS.
    Supports English, Hindi, Telugu, and Tamil.
    """
    def __init__(self, provider: str = None):
        self.provider = provider or config.get("voice.tts.provider", "edge-tts")
        self.output_dir = os.path.join(config.base_dir, "data", "processed")
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Load voices from config
        self.voices = {
            "en": config.get("voice.tts.voice_en", EDGE_VOICES["en"]),
            "hi": config.get("voice.tts.voice_hi", EDGE_VOICES["hi"]),
            "te": config.get("voice.tts.voice_te", EDGE_VOICES["te"]),
            "ta": config.get("voice.tts.voice_ta", EDGE_VOICES["ta"]),
        }

    def generate_speech(self, text: str, lang: str = "en") -> str:
        """
        Converts text to an audio file and returns the path to the saved MP3 file.
        """
        lang = lang.lower()
        if lang not in self.voices:
            logger.warning(f"Unsupported TTS language: {lang}. Defaulting to English ('en').")
            lang = "en"
            
        # Create output file path based on hash of content + language + provider
        filename = f"tts_{get_text_hash(text + lang + self.provider)}.mp3"
        output_path = os.path.join(self.output_dir, filename)
        
        # If file already exists, return cached audio directly
        if os.path.exists(output_path):
            logger.info(f"Using cached TTS audio: {output_path}")
            return output_path
            
        logger.info(f"Generating speech using {self.provider} for language {lang}. Text: '{text[:40]}...'")
        
        if self.provider == "edge-tts":
            try:
                self._generate_edge_tts(text, self.voices[lang], output_path)
            except Exception as e:
                logger.error(f"Edge TTS failed: {e}. Falling back to gTTS.")
                self._generate_gtts(text, lang, output_path)
        else:
            self._generate_gtts(text, lang, output_path)
            
        return output_path

    def _generate_gtts(self, text: str, lang: str, output_path: str):
        """Generates speech using Google TTS (requires internet)."""
        # gTTS uses ISO 639-1 language codes ('en', 'hi', 'te', 'ta')
        tts = gTTS(text=text, lang=lang, slow=False)
        tts.save(output_path)
        logger.info(f"gTTS audio saved to {output_path}")

    def _generate_edge_tts(self, text: str, voice: str, output_path: str):
        """Generates speech using Edge TTS (async, requires internet)."""
        import edge_tts
        
        async def communicate():
            communicate = edge_tts.Communicate(text, voice)
            await communicate.save(output_path)
            
        # Standard sync runner for async edge-tts
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
            
        if loop and loop.is_running():
            # If inside an existing event loop, run in a separate thread to avoid nested loops block
            import threading
            from concurrent.futures import ThreadPoolExecutor
            with ThreadPoolExecutor(1) as executor:
                executor.submit(asyncio.run, communicate()).result()
        else:
            asyncio.run(communicate())
            
        logger.info(f"Edge-TTS audio saved to {output_path}")
