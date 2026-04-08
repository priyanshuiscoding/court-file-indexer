from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    APP_NAME: str = "Court File Indexer Backend"
    APP_ENV: str = "local"
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    API_V1_PREFIX: str = "/api/v1"
    LOG_LEVEL: str = "INFO"
    SECRET_KEY: str = "change-me"

    POSTGRES_SERVER: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "court_indexer"
    POSTGRES_USER: str = "court_user"
    POSTGRES_PASSWORD: str = "court_pass"

    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0

    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    QDRANT_COLLECTION: str = "court_documents"
    EMBEDDING_VECTOR_SIZE: int = 1024
    QDRANT_TOP_K: int = 8
    CHAT_CONTEXT_TOP_K: int = 6
    CHAT_MAX_HISTORY: int = 12
    CHAT_GENERATION_TIMEOUT_SECONDS: int = 45

    STORAGE_ROOT: str = "./storage"
    PDF_STORAGE_DIR: str = "./storage/pdfs"
    RENDER_STORAGE_DIR: str = "./storage/rendered"
    OCR_STORAGE_DIR: str = "./storage/ocr"
    EXPORT_STORAGE_DIR: str = "./storage/exports"
    LOG_STORAGE_DIR: str = "./storage/logs"
    MAPPING_SHEET_PATH: str = "./storage/config/document_mapping.xlsx"
    MAPPING_SHEET_NAME: str = "Sheet1"
    MAPPING_REFRESH_SECONDS: int = 60

    DEFAULT_INDEX_SCAN_START: int = 1
    DEFAULT_INDEX_SCAN_END: int = 10
    DEFAULT_BATCH_CHUNK_SIZE: int = 10
    DEFAULT_QUEUE_NAME: str = "index_queue"
    TASK_HEARTBEAT_SECONDS: int = 30
    STUCK_TASK_SECONDS: int = 900

    OCR_ENGINE: str = "paddle"
    OCR_LANGUAGES: str = "en,hi"
    OCR_USE_ANGLE_CLS: bool = True
    OCR_RENDER_DPI: int = 220
    OCR_RENDER_FORMAT: str = "png"
    INDEX_MIN_CANDIDATE_SCORE: float = 2.0
    INDEX_CONTINUATION_MIN_SCORE: float = 1.2
    ENABLE_HINDI_FALLBACK: bool = True
    ENABLE_CONTENT_GENERATED_INDEX_FALLBACK: bool = True
    TESSERACT_CMD: str = "tesseract"

    USE_VLM_FALLBACK: bool = True
    ENABLE_CHAT: bool = True
    ENABLE_QDRANT: bool = True

    LOCAL_EMBEDDING_MODEL: str = "BAAI/bge-m3"
    LOCAL_RERANKER_MODEL: str = "BAAI/bge-reranker-v2-m3"
    LOCAL_CHAT_MODEL: str = "Qwen/Qwen2.5-3B-Instruct"
    LOCAL_VLM_MODEL: str = "Qwen/Qwen2.5-VL-7B-Instruct"

    @property
    def sqlalchemy_database_uri(self) -> str:
        return (
            f"postgresql+psycopg2://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def redis_url(self) -> str:
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    @property
    def qdrant_url(self) -> str:
        return f"http://{self.QDRANT_HOST}:{self.QDRANT_PORT}"


@lru_cache
def get_settings() -> Settings:
    return Settings()
