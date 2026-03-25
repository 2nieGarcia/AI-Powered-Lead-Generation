from pydantic_settings import BaseSettings, SettingsConfigDict
import os

class Settings(BaseSettings):
    SUPABASE_URL: str
    SUPABASE_KEY: str
    
    # Original AI-Powered Lead Generator settings
    GROQ_API_URL: str = "https://api.groq.com/openai/v1/chat/completions"
    
    # Merged Digital Footprint Agent settings
    GROQ_API_KEY: str | None = None
    GEMINI_API_KEY: str | None = None
    
    GEMINI_RPM_LIMIT: int = int(os.getenv('GEMINI_RPM_LIMIT', 15))
    GROQ_RPM_LIMIT: int = int(os.getenv('GROQ_RPM_LIMIT', 30))
    
    GEMINI_MODEL: str = "gemini-2.5-flash"
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    
    GEMINI_BASE_URL: str = "https://generativelanguage.googleapis.com/v1beta/models"

    DDG_MAX_RESULTS: int = 3

    PORT: int = int(os.getenv('PORT', 8000))

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()

# Backwards compatibility reference for footprint agent refactored codebase
Config = settings



