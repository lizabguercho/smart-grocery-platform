import os

import psycopg
from dotenv import load_dotenv

load_dotenv()


def get_connection() -> psycopg.Connection:
    """Create a connection to the local PostgreSQL database."""

    return psycopg.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
    )


def get_remote_connection() -> psycopg.Connection:
    """Create a connection to the remote PostgreSQL database."""

    return psycopg.connect(
        host=os.getenv("REMOTE_DB_HOST"),
        port=os.getenv("REMOTE_DB_PORT"),
        dbname=os.getenv("REMOTE_DB_NAME"),
        user=os.getenv("REMOTE_DB_USER"),
        password=os.getenv("REMOTE_DB_PASSWORD"),
        connect_timeout=15,
    )
