from src.database_loader.connection import get_connection

def main():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TEMP TABLE test_insert (
                    id INTEGER,
                    message TEXT
                );
            """)
            cur.execute("""
                INSERT INTO test_insert (id, message)
                VALUES (%s, %s);
                """,
            (1, "Hello from Python!")
            )
            cur.execute("SELECT id, message FROM test_insert;")

            row = cur.fetchone()

            print(row)


if __name__ == "__main__":
    main()