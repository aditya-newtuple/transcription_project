import psycopg2
from psycopg2 import OperationalError, sql
import sys

# Connection parameters
DB_CONFIG = {
    'dbname': 'Transcriber_local',
    'user': 'root',
    'password': 'root',
    'host': 'localhost',   # not pg-database-hilliard
    'port': 5433,          # host-mapped port
    'connect_timeout': 5
}

def test_postgres_connection():
    try:
        print("Attempting to connect...")
        conn = psycopg2.connect(**DB_CONFIG)
        print("✅ Connected to PostgreSQL successfully.")

        # Optional: run a test query
        with conn.cursor() as cursor:
            cursor.execute("SELECT version();")
            version = cursor.fetchone()
            print("PostgreSQL version:", version[0])

        conn.close()
        print("Connection closed.")

    except OperationalError as e:
        print("❌ OperationalError:", e)
        sys.exit(1)

    except Exception as e:
        print("❌ Unexpected error:", e)
        sys.exit(1)

if __name__ == "__main__":
    test_postgres_connection()