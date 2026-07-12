"""
Configuración centralizada del agente de videos infantiles
"""
import os
from pathlib import Path
from dotenv import load_dotenv
from typing import Tuple

# Cargar variables de entorno
load_dotenv()

class Config:
    """Configuración principal de la aplicación"""
    
    # OpenAI Configuration
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4")
    
    # YouTube Configuration
    YOUTUBE_CLIENT_ID = os.getenv("YOUTUBE_CLIENT_ID", "")
    YOUTUBE_CLIENT_SECRET = os.getenv("YOUTUBE_CLIENT_SECRET", "")
    YOUTUBE_REFRESH_TOKEN = os.getenv("YOUTUBE_REFRESH_TOKEN", "")
    
    # Video Configuration
    VIDEO_WIDTH = int(os.getenv("VIDEO_WIDTH", "1280"))
    VIDEO_HEIGHT = int(os.getenv("VIDEO_HEIGHT", "720"))
    VIDEO_FPS = int(os.getenv("VIDEO_FPS", "30"))
    VIDEO_DURATION = int(os.getenv("VIDEO_DURATION", "120"))
    
    # Audio Configuration
    VOICE_LANGUAGE = os.getenv("VOICE_LANGUAGE", "es")
    VOICE_SLOW = os.getenv("VOICE_SLOW", "False").lower() == "true"
    
    # Directories
    OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "./output"))
    VIDEOS_DIR = OUTPUT_DIR / "videos"
    TEMP_DIR = OUTPUT_DIR / "temp"
    LOGS_DIR = OUTPUT_DIR / "logs"
    
    # Create directories if they don't exist
    for directory in [OUTPUT_DIR, VIDEOS_DIR, TEMP_DIR, LOGS_DIR]:
        directory.mkdir(parents=True, exist_ok=True)
    
    # Logging
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE = LOGS_DIR / "agent.log"
    
    # Scheduler Configuration
    SCHEDULER_ENABLED = os.getenv("SCHEDULER_ENABLED", "True").lower() == "true"
    SCHEDULER_TIMEZONE = os.getenv("SCHEDULER_TIMEZONE", "UTC")
    
    # Colors (RGB)
    PRIMARY_COLOR = tuple(map(int, os.getenv("PRIMARY_COLOR", "255,100,150").split(",")))
    SECONDARY_COLOR = tuple(map(int, os.getenv("SECONDARY_COLOR", "100,200,255").split(",")))
    BACKGROUND_COLOR = tuple(map(int, os.getenv("BACKGROUND_COLOR", "255,255,240").split(",")))
    
    # Story Configuration
    STORY_TONE = os.getenv("STORY_TONE", "friendly,educational,fun").split(",")
    STORY_MIN_LENGTH = int(os.getenv("STORY_MIN_LENGTH", "5"))
    STORY_MAX_LENGTH = int(os.getenv("STORY_MAX_LENGTH", "15"))
    
    @classmethod
    def validate(cls) -> bool:
        """Valida que las configuraciones requeridas estén presentes"""
        required_keys = ["OPENAI_API_KEY"]
        missing = [key for key in required_keys if not getattr(cls, key)]
        
        if missing:
            print(f"❌ Configuración faltante: {', '.join(missing)}")
            print("📝 Por favor, configura estas variables en .env")
            return False
        
        print("✅ Configuración validada correctamente")
        return True


if __name__ == "__main__":
    Config.validate()
