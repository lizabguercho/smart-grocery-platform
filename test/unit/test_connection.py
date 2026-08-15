from unittest.mock import patch

from src.database_loader.connection import get_connection


def test_get_connection_passes_environment_variables(monkeypatch) -> None:
    monkeypatch.setenv("DB_HOST", "db.example")
    monkeypatch.setenv("DB_PORT", "5433")
    monkeypatch.setenv("DB_NAME", "grocery")
    monkeypatch.setenv("DB_USER", "app")
    monkeypatch.setenv("DB_PASSWORD", "secret")

    with patch("src.database_loader.connection.psycopg.connect") as connect:
        connect.return_value = object()
        get_connection()

    connect.assert_called_once_with(
        host="db.example",
        port="5433",
        dbname="grocery",
        user="app",
        password="secret",
    )


def test_get_connection_allows_missing_environment_variables(
    monkeypatch,
) -> None:
    for name in ("DB_HOST", "DB_PORT", "DB_NAME", "DB_USER", "DB_PASSWORD"):
        monkeypatch.delenv(name, raising=False)

    with patch("src.database_loader.connection.psycopg.connect") as connect:
        connect.return_value = object()
        get_connection()

    connect.assert_called_once_with(
        host=None,
        port=None,
        dbname=None,
        user=None,
        password=None,
    )
