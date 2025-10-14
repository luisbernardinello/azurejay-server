import logging
from typing import Optional
from groq import Groq
from decouple import config

# Configure Groq client
client = Groq(api_key=config("GROQ_API_KEY"))

async def convert_audio_to_text(audio_file_path: str, model: str = "whisper-large-v3-turbo") -> Optional[str]:
    """
    Convert audio file to text using Groq Whisper API.
    
    Args:
        audio_file_path: Path to the audio file
        model: Whisper model to use (whisper-large-v3-turbo or whisper-large-v3)
    
    Returns:
        Transcribed text if successful, None if failed
    """
    try:
        logging.info(f"Transcribing audio file: {audio_file_path}")
        
        with open(audio_file_path, "rb") as audio_file:
            # Groq Whisper for transcription
            transcription = client.audio.transcriptions.create(
                file=audio_file,
                model=model,
                language="en",
                temperature=0.0,
                response_format="json"
            )
        
        transcribed_text = transcription.text.strip()
        
        if not transcribed_text:
            logging.warning("Transcription resulted in empty text")
            return None
        
        logging.info(f"Successfully transcribed audio: {transcribed_text}")
        return transcribed_text
        
    except Exception as e:
        logging.error(f"Groq API error during transcription: {e}")
        return None

async def convert_audio_to_text_with_metadata(
    audio_file_path: str, 
    model: str = "whisper-large-v3-turbo",
    include_timestamps: bool = False
) -> Optional[dict]:
    """
    Convert audio file to text with detailed metadata using Groq Whisper API.
    
    Args:
        audio_file_path: Path to the audio file
        model: Whisper model to use (whisper-large-v3-turbo or whisper-large-v3)
        include_timestamps: Whether to include word-level timestamps
    
    Returns:
        Dictionary with transcription and metadata if successful, None if failed
    """
    try:
        logging.info(f"Transcribing audio file with metadata: {audio_file_path}")
        
        timestamp_granularities = ["segment"]
        if include_timestamps:
            timestamp_granularities.append("word")
        
        with open(audio_file_path, "rb") as audio_file:
            # Groq Whisper for transcription with verbose output
            transcription = client.audio.transcriptions.create(
                file=audio_file,
                model=model,
                language="en",
                temperature=0.0,
                response_format="verbose_json",
                timestamp_granularities=timestamp_granularities
            )
        
        if not transcription.text.strip():
            logging.warning("Transcription resulted in empty text")
            return None
        
        result = {
            "text": transcription.text.strip(),
            "language": transcription.language,
            "duration": transcription.duration,
            "segments": transcription.segments if hasattr(transcription, 'segments') else [],
            "words": transcription.words if hasattr(transcription, 'words') and include_timestamps else []
        }
        
        return result
        
    except Exception as e:
        logging.error(f"Groq API error during transcription with metadata: {e}")
        return None

async def convert_audio_to_text_optimized(audio_file_path: str, context: str = "") -> Optional[str]:
    """
    Convert audio file to text with optimized settings for English learning context.
    
    Args:
        audio_file_path: Path to the audio file
        context: Context or prompt to guide transcription style
    
    Returns:
        Transcribed text if successful, None if failed
    """
    try:
        logging.info(f"Transcribing audio file (optimized): {audio_file_path}")
        
        # whisper-large-v3 for accuracy when context is important
        model = "whisper-large-v3" if context else "whisper-large-v3-turbo"
        
        with open(audio_file_path, "rb") as audio_file:
            transcription_params = {
                "file": audio_file,
                "model": model,
                "language": "en",
                "temperature": 0.0,
                "response_format": "json"
            }
            
            # Add prompt if context is provided (max 224 tokens)
            if context:
                transcription_params["prompt"] = context[:224]
            
            transcription = client.audio.transcriptions.create(**transcription_params)
        
        transcribed_text = transcription.text.strip()
        
        if not transcribed_text:
            logging.warning("Transcription resulted in empty text")
            return None
        
        logging.info(f"Successfully transcribed audio (optimized): {transcribed_text}")
        return transcribed_text
        
    except Exception as e:
        logging.error(f"Groq API error during optimized transcription: {e}")
        return None

def get_supported_audio_formats() -> list:
    """
    Get list of supported audio formats for Groq transcription.
    
    Returns:
        List of supported file extensions
    """
    return ["flac", "mp3", "mp4", "mpeg", "mpga", "m4a", "ogg", "wav", "webm"]

def get_audio_file_limits() -> dict:
    """
    Get audio file size and duration limits for Groq API.
    
    Returns:
        Dictionary with size and duration limits
    """
    return {
        "max_file_size_mb": 25,  # 25MB for free tier, 100MB for dev tier
        "min_duration_seconds": 0.01,
        "min_billed_duration_seconds": 10  # Minimum billing is 10 seconds
    }

def get_available_models() -> dict:
    """
    Get available Whisper models with their characteristics.
    
    Returns:
        Dictionary with model information
    """
    return {
        "whisper-large-v3-turbo": {
            "cost_per_hour": 0.04,
            "language_support": "Multilingual",
            "transcription_support": True,
            "translation_support": False,
            "real_time_speed_factor": 216,
            "word_error_rate": "12%",
            "recommended_for": "Fast transcription with good price/performance"
        },
        "whisper-large-v3": {
            "cost_per_hour": 0.111,
            "language_support": "Multilingual", 
            "transcription_support": True,
            "translation_support": True,
            "real_time_speed_factor": 189,
            "word_error_rate": "10.3%",
            "recommended_for": "Error-sensitive applications requiring highest accuracy"
        }
    }

def validate_audio_file(audio_file_path: str) -> tuple[bool, str]:
    """
    Validate audio file before transcription.
    
    Args:
        audio_file_path: Path to the audio file
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    import os
    
    try:
        if not os.path.exists(audio_file_path):
            return False, "Audio file not found"
        
        file_size_mb = os.path.getsize(audio_file_path) / (1024 * 1024)
        limits = get_audio_file_limits()
        
        if file_size_mb > limits["max_file_size_mb"]:
            return False, f"File size ({file_size_mb:.1f}MB) exceeds limit ({limits['max_file_size_mb']}MB)"
        
        file_extension = audio_file_path.lower().split('.')[-1]
        supported_formats = get_supported_audio_formats()
        
        if file_extension not in supported_formats:
            return False, f"Unsupported file format. Supported: {', '.join(supported_formats)}"
        
        return True, "Valid audio file"
        
    except Exception as e:
        return False, f"Error validating file: {str(e)}"