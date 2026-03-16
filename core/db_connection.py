from typing import List
from urllib.parse import quote_plus

from langchain_community.utilities import SQLDatabase
from sqlalchemy import create_engine

from config import settings


def build_db_uri() -> str:
    server = settings.MSSQL_HOST.strip()
    port = settings.MSSQL_PORT.strip()
    if port:
        server = f"{server}:{port}"

    dialect = settings.MSSQL_SQLALCHEMY_DRIVER.strip().lower()
    trust_server_certificate = str(settings.MSSQL_TRUST_SERVER_CERTIFICATE).lower()

    if dialect == "pyodbc":
        driver_q = settings.MSSQL_DRIVER.strip().replace(" ", "+")
        odbc_server = server.replace(":", ",")
        if settings.MSSQL_WINDOWS_AUTH:
            return (
                f"mssql+pyodbc://@{odbc_server}/{settings.MSSQL_DATABASE}"
                f"?driver={driver_q}"
                f"&trusted_connection=yes"
                f"&TrustServerCertificate={trust_server_certificate}"
            )

        safe_password = quote_plus(settings.MSSQL_PASSWORD)
        return (
            f"mssql+pyodbc://{settings.MSSQL_USER}:{safe_password}"
            f"@{odbc_server}/{settings.MSSQL_DATABASE}"
            f"?driver={driver_q}"
            f"&TrustServerCertificate={trust_server_certificate}"
        )

    if dialect == "pymssql":
        if settings.MSSQL_WINDOWS_AUTH:
            raise ValueError(
                "MSSQL_WINDOWS_AUTH=true chi duoc ho tro khi MSSQL_SQLALCHEMY_DRIVER=pyodbc."
            )

        safe_password = quote_plus(settings.MSSQL_PASSWORD)
        return (
            f"mssql+pymssql://{settings.MSSQL_USER}:{safe_password}"
            f"@{server}/{settings.MSSQL_DATABASE}"
            "?charset=utf8"
        )

    raise ValueError(
        "MSSQL_SQLALCHEMY_DRIVER khong hop le. Ho tro: 'pymssql' hoac 'pyodbc'."
    )


def create_db_engine():
    return create_engine(DB_URI, pool_pre_ping=True)


def test_connection() -> List[str]:
    db = SQLDatabase.from_uri(build_db_uri())
    return list(db.get_usable_table_names())


DB_URI = build_db_uri()
