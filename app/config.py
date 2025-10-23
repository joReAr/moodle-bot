from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    LOCAL_STORAGE_DIR: str = "./data"
    DB_URL: str = "sqlite:///./local.db"
    WHOOSH_DIR: str = "./indices/whoosh"
    FAISS_INDEX_PATH: str = "./indices/course.faiss"

    USE_TTS: bool = False
    TTS_ENGINE: str = "piper"


    GEMINI_API_KEY: str = Field(default="", description="Set your Gemini API key or use environment variable")
    GEMINI_MODEL: str = "gemini-2.0-flash"

settings = Settings()  # importable
