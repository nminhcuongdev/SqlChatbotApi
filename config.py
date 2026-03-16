from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    OPENAI_API_KEY: str
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"
    OPENAI_CHAT_MODEL: str = "gpt-4.1"

    MSSQL_HOST: str
    MSSQL_PORT: str = "1433"
    MSSQL_USER: str = "sa"
    MSSQL_PASSWORD: str = ""
    MSSQL_DATABASE: str
    MSSQL_SQLALCHEMY_DRIVER: str = "pymssql"
    MSSQL_DRIVER: str = "ODBC Driver 18 for SQL Server"
    MSSQL_WINDOWS_AUTH: bool = False
    MSSQL_TRUST_SERVER_CERTIFICATE: bool = True

    CHROMA_PERSIST_DIR: str = "./chroma_db"

    CHUNK_SIZE: int = 400
    CHUNK_OVERLAP: int = 40
    TOP_K: int = 5

    class Config:
        env_file = ".env"


settings = Settings()
