
from pathlib import Path
import os

import mysql.connector
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash

BASE_DIR = Path(__file__).resolve().parent
SQL_DIR = BASE_DIR / "sql"

load_dotenv(BASE_DIR / ".env")

DEMO_PASSWORD = "Password@123"


def get_connection():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST", "localhost"),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", ""),
        database=os.getenv("DB_NAME", "college_placement_db"),
    )


def execute_sql_file(cursor, file_path):
    if not file_path.exists():
        raise FileNotFoundError(f"Missing file: {file_path}")

    content = file_path.read_text(encoding="utf-8")
    statements = [
        item.strip()
        for item in content.split(";")
        if item.strip()
    ]

    for number, statement in enumerate(statements, start=1):
        try:
            cursor.execute(statement)
        except Exception as error:
            raise RuntimeError(
                f"{file_path.name}, statement {number}: {error}"
            ) from error

    return len(statements)


def main():
    connection = None
    cursor = None

    try:
        connection = get_connection()
        cursor = connection.cursor()

        seed_file = SQL_DIR / "seed.sql"
        views_file = SQL_DIR / "views.sql"

        if not seed_file.exists():
            raise FileNotFoundError(f"Missing file: {seed_file}")

        if not views_file.exists():
            raise FileNotFoundError(f"Missing file: {views_file}")

        print("Connected to MySQL.")

        print("\nLoading demo data...")
        seed_count = execute_sql_file(cursor, seed_file)

        # Generate a valid password hash for the demo accounts.
        password_hash = generate_password_hash(DEMO_PASSWORD)

        cursor.execute(
            """
            UPDATE users
            SET password_hash = %s
            WHERE email IN (
                'aarav@example.com',
                'diya@example.com',
                'rohan@example.com',
                'ananya@example.com',
                'ishaan@example.com',
                'meera@example.com',
                'kabir@example.com',
                'sana@example.com',
                'arjun@example.com',
                'priya@example.com',
                'rahul@example.com',
                'neha@example.com',
                'admin@example.com'
            )
            """,
            (password_hash,),
        )

        connection.commit()
        print(f"seed.sql: {seed_count} statements executed.")
        print("Demo password hashes generated successfully.")

        print("\nLoading report views...")
        views_count = execute_sql_file(cursor, views_file)
        connection.commit()
        print(f"views.sql: {views_count} statements executed.")

        tables = [
            "users",
            "students",
            "companies",
            "placement_drives",
            "student_skills",
            "drive_skills",
            "applications",
            "selection_results",
        ]

        print("\nDatabase row counts:")

        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM `{table}`")
            count = cursor.fetchone()[0]
            print(f"{table:<22} {count}")

        print("\nSeeding completed successfully.")
        print("Demo login password:", DEMO_PASSWORD)
        print("Demo admin email: admin@example.com")
        print("Demo student email: aarav@example.com")

    except Exception as error:
        if connection is not None:
            try:
                connection.rollback()
            except mysql.connector.Error:
                pass

        print(f"\nSeeding failed: {error}")

    finally:
        if cursor is not None:
            cursor.close()

        if connection is not None:
            connection.close()


if __name__ == "__main__":
    main()
