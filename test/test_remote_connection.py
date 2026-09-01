from src.database_loader.connection import get_remote_connection


connection = get_remote_connection()

with connection.cursor() as cursor:
    cursor.execute("SELECT current_user;")
    result = cursor.fetchone()

print(result)

connection.close()