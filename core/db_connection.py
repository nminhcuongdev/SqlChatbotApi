"""
Xây dựng URI kết nối MSSQL từ settings (.env).
Không nhận thông tin kết nối từ request — tất cả đọc từ config.
"""

from typing import List
from urllib.parse import quote_plus
from langchain_community.utilities import SQLDatabase
from config import settings


def build_db_uri() -> str:
    """Xây dựng SQLAlchemy URI từ settings (.env)."""
    server_part = settings.MSSQL_HOST.strip()
    if settings.MSSQL_PORT.strip():
        server_part = f"{server_part},{settings.MSSQL_PORT.strip()}"

    driver_q = settings.MSSQL_DRIVER.strip().replace(" ", "+")

    if settings.MSSQL_WINDOWS_AUTH:
        return (
            f"mssql+pyodbc://@{server_part}/{settings.MSSQL_DATABASE}"
            f"?driver={driver_q}"
            f"&trusted_connection=yes"
            f"&TrustServerCertificate=yes"
        )
    else:
        safe_password = quote_plus(settings.MSSQL_PASSWORD)
        return (
            f"mssql+pyodbc://{settings.MSSQL_USER}:{safe_password}"
            f"@{server_part}/{settings.MSSQL_DATABASE}"
            f"?driver={driver_q}"
            f"&TrustServerCertificate=yes"
        )


def test_connection() -> List[str]:
    """Thử kết nối và trả về danh sách bảng."""
    db = SQLDatabase.from_uri(build_db_uri())
    return list(db.get_usable_table_names())


# URI dùng chung — build 1 lần khi module load
DB_URI = build_db_uri()

