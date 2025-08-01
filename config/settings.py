from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    gemini_api_key: str
    gemini_model: str = "gemini-1.5-flash"
    gemini_temperature: float = 0.7
    gemini_max_tokens: int = 2048
    
    vector_db_path: str = "./data/vector_store"
    chunk_size: int = 1000
    chunk_overlap: int = 200
    embedding_model: str = "all-MiniLM-L6-v2"
    
    app_name: str = "FenmoAI Offer Letter Generator"
    debug: bool = True
    log_level: str = "INFO"
    
    assets_path: str = "./assets"
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()