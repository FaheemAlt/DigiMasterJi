# AI Services Package
# Contains services for LLM (Ollama), STT (Whisper), and TTS (gTTS)
#
# Use lazy imports to avoid loading heavy ML libraries until needed:
#   from app.services.llm_service import LLMService
#   from app.services.stt_service import STTService
#   from app.services.tts_service import TTSService

__all__ = ["LLMService", "STTService", "TTSService"]


def __getattr__(name):
    """Lazy import to avoid loading heavy ML models on package import."""
    if name == "LLMService":
        from app.services.llm_service import LLMService
        return LLMService
    elif name == "STTService":
        from app.services.stt_service import STTService
        return STTService
    elif name == "TTSService":
        from app.services.tts_service import TTSService
        return TTSService
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

