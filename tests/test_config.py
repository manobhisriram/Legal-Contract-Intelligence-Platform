"""Configuration parsing and database URL normalisation."""
from backend.core.config import (
    Settings,
    normalize_async_database_url,
    normalize_sync_database_url,
)


def test_managed_postgres_url_is_converted_for_asyncpg():
    url = normalize_async_database_url("postgres://u:p@host:5432/db?sslmode=require")
    assert url == "postgresql+asyncpg://u:p@host:5432/db?ssl=require"


def test_async_url_is_idempotent():
    url = "postgresql+asyncpg://u:p@host/db?ssl=require"
    assert normalize_async_database_url(url) == url


def test_sync_url_uses_psycopg2_style():
    url = normalize_sync_database_url("postgresql+asyncpg://u:p@host/db?ssl=require")
    assert url == "postgresql://u:p@host/db?sslmode=require"


def test_sync_url_is_derived_from_async_url_when_missing():
    s = Settings(database_url="postgres://u:p@host/db?sslmode=require", database_url_sync="")
    assert s.database_url.startswith("postgresql+asyncpg://")
    assert s.database_url_sync == "postgresql://u:p@host/db?sslmode=require"


def test_explicit_sync_url_is_preserved():
    s = Settings(
        database_url="postgresql+asyncpg://u:p@host/db",
        database_url_sync="postgresql://u:p@other/db",
    )
    assert s.database_url_sync == "postgresql://u:p@other/db"


def test_empty_urls_stay_empty():
    s = Settings(database_url="", database_url_sync="")
    assert s.database_url == "" and s.database_url_sync == ""


def test_cors_origin_list_parsing():
    s = Settings(cors_origins="https://a.example, https://b.example")
    assert s.cors_origin_list == ["https://a.example", "https://b.example"]
    assert Settings(cors_origins="").cors_origin_list == ["*"]
