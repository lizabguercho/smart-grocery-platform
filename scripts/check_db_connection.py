from src.database_loader.connection import get_connection


def main() -> None:
    try:
        with get_connection() as conn:
            print("Successfully connected to PostgreSQL!")

            with conn.cursor() as cur:
                cur.execute("SELECT current_database();")
                database_name = cur.fetchone()[0]

                print(f"Connected database: {database_name}")

    except Exception as error:
        print(f"Connection failed: {error}")
        raise SystemExit(1) from error


if __name__ == "__main__":
    main()
