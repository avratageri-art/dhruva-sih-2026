import os
from pydantic_settings import BaseSettings, SettingsConfigDict

_backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_project_dir = os.path.dirname(_backend_dir)
_env_path = os.path.join(_project_dir, ".env")

class Settings(BaseSettings):
    PROJECT_NAME: str = "DHRUVA"
    DATABASE_URL: str = "sqlite:///./darktrace.db"
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USERNAME: str = "neo4j"
    NEO4J_PASSWORD: str = "change_me_local_only"
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"
    
    MODEL_NAME: str = "sentence-transformers/all-MiniLM-L6-v2"
    MODEL_PATH: str = "./models/baseline"
    MLFLOW_TRACKING_URI: str = "sqlite:///mlflow.db"
    API_URL: str = "http://localhost:8000"

    # Tor SOCKS5 Proxy Configuration (Single Source of Truth)
    TOR_SOCKS_HOST: str = "127.0.0.1"
    TOR_SOCKS_PORT: int = 9050

    # Optional, analyst-supplied Robin search engines. Empty by default so a
    # fresh local setup never contacts real-world search infrastructure.
    ROBIN_SEARCH_ENGINES_JSON: str = "[]"

    # DeepDarkCTI Integration Settings
    DEEPDARKCTI_REFRESH_INTERVAL: int = 3600    # seconds between catalogue refreshes
    DEEPDARKCTI_COLLECT_INTERVAL: int = 300     # seconds between collection cycles
    DEEPDARKCTI_MAX_SOURCES_PER_CYCLE: int = 5  # max sources per cycle (rate limiting)
    DEEPDARKCTI_COLLECT_TIMEOUT: int = 20       # seconds per source collection timeout

    @property
    def TOR_SOCKS_PROXY(self) -> str:
        return f"socks5h://{self.TOR_SOCKS_HOST}:{self.TOR_SOCKS_PORT}"

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]
    
    model_config = SettingsConfigDict(
        env_file=(_env_path, os.path.join(_backend_dir, ".env"), ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()

