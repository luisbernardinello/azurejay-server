import requests
import logging
from typing import Optional
from decouple import config

ELEVEN_LABS_API_KEY = config("ELEVEN_LABS_API_KEY")

# Voice IDs for different characters
VOICE_IDS = {
    "rachel": "21m00Tcm4TlvDq8ikWAM",  # Rachel voice
    "shaun": "mTSvIrm2hmcnOvb21nW2",   # Shaun voice
    "antoni": "ErXwobaYiN019PkySvjV"    # Antoni voice
}

def convert_text_to_speech(
    message: str, 
    voice: str = "rachel",
    stability: float = 0.5,
    similarity_boost: float = 0.75
) -> Optional[bytes]:
    """
    Convert text to speech using ElevenLabs API.
    
    Args:
        message: The text to convert to speech
        voice: The voice to use (default: "rachel")
        stability: Voice stability (0.0 to 1.0, default: 0.5)
        similarity_boost: Voice similarity boost (0.0 to 1.0, default: 0.75)
    
    Returns:
        Audio data as bytes if successful, None if failed
    """
    if not ELEVEN_LABS_API_KEY:
        logging.error("ElevenLabs API key not found in environment variables")
        return None
    
    if not message.strip():
        logging.error("Empty message provided for TTS conversion")
        return None
    
    # Get voice ID
    voice_id = VOICE_IDS.get(voice.lower(), VOICE_IDS["rachel"])
    
    # Request body
    body = {
        "text": message,
        "voice_settings": {
            "stability": stability,
            "similarity_boost": similarity_boost
        }
    }
    
    # Request headers
    headers = {
        "xi-api-key": ELEVEN_LABS_API_KEY,
        "Content-Type": "application/json",
        "accept": "audio/mpeg"
    }
    
    # API endpoint
    endpoint = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    
    try:       
        response = requests.post(endpoint, json=body, headers=headers, timeout=30)
        
        if response.status_code == 200:
            return response.content
        else:
            logging.error(f"ElevenLabs API error: {response.status_code} - {response.text}")
            return None
            
    except requests.exceptions.Timeout:
        logging.error("ElevenLabs API timeout")
        return None
    except requests.exceptions.ConnectionError:
        logging.error("ElevenLabs API connection error")
        return None
    except Exception as e:
        logging.error(f"Unexpected error in text-to-speech conversion: {e}")
        return None

def get_available_voices() -> dict:
    """
    Get list of available voices.
    
    Returns:
        Dictionary of available voice names and IDs
    """
    return VOICE_IDS.copy()