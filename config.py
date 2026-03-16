from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ── OpenAI ────────────────────────────────────────────────────────────────
    OPENAI_API_KEY: str
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"
    OPENAI_CHAT_MODEL: str = "gpt-4.1"

    # ── MSSQL ─────────────────────────────────────────────────────────────────
    MSSQL_HOST: str
    MSSQL_PORT: str = ""                              # để trống = dùng port mặc định 1433
    MSSQL_USER: str = "sa"
    MSSQL_PASSWORD: str = ""
    MSSQL_DATABASE: str
    MSSQL_DRIVER: str = "ODBC Driver 17 for SQL Server"
    MSSQL_WINDOWS_AUTH: bool = True                  # True = Trusted Connection

    # ── ChromaDB ──────────────────────────────────────────────────────────────
    CHROMA_PERSIST_DIR: str = "./chroma_db"

    # ── RAG ───────────────────────────────────────────────────────────────────
    CHUNK_SIZE: int = 400
    CHUNK_OVERLAP: int = 40
    TOP_K: int = 5

    class Config:
        env_file = ".env"


settings = Settings()
