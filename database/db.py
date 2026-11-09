
import sqlite3
import os
from dotenv import load_dotenv

# Environment variables load karein
load_dotenv()

# Project folder ka correct path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Local SQLite database ka path
DATABASE_PATH = os.path.join(BASE_DIR, "database", "library.db")

# Render par Supabase ka DATABASE_URL milega
DATABASE_URL = os.getenv("DATABASE_URL")


class PostgresConnection:

    def __init__(self, connection):
        self.connection = connection

    def execute(self, query, parameters=()):
        # SQLite placeholders (?) ko PostgreSQL placeholders (%s) mein badlein
        query = query.replace("?", "%s")
        return self.connection.execute(query, parameters)

    def commit(self):
        self.connection.commit()

    def rollback(self):
        self.connection.rollback()

    def close(self):
        self.connection.close()

    def __getattr__(self, name):
        return getattr(self.connection, name)


def get_db_connection():

    # Agar DATABASE_URL available hai to PostgreSQL use hoga
    if DATABASE_URL:

        import psycopg
        from psycopg.rows import dict_row

        connection = psycopg.connect(
            DATABASE_URL,
            row_factory=dict_row
        )

        return PostgresConnection(connection)

    # Warna local SQLite use hoga
    connection = sqlite3.connect(DATABASE_PATH)

    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")

    return connection


def create_tables():

    # Supabase tables pehle hi create kiye ja chuke hain
    if DATABASE_URL:
        return

    # Sirf local SQLite ke liye tables create honge
    connection = get_db_connection()

    connection.execute("""
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            category TEXT NOT NULL,
            quantity INTEGER NOT NULL
        )
    """)

    connection.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            roll_no TEXT NOT NULL UNIQUE,
            department TEXT NOT NULL,
            semester INTEGER NOT NULL,
            email TEXT
        )
    """)

    connection.execute("""
        CREATE TABLE IF NOT EXISTS borrow_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            book_id INTEGER NOT NULL,
            borrow_date TEXT NOT NULL,
            due_date TEXT NOT NULL,
            return_date TEXT,
            status TEXT NOT NULL DEFAULT 'Borrowed',

            FOREIGN KEY (student_id) REFERENCES students(id),
            FOREIGN KEY (book_id) REFERENCES books(id)
        )
    """)

    connection.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            email TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('admin', 'student'))
        )
    """)

    connection.commit()
    connection.close()


if __name__ == "__main__":
    create_tables()
    print("Database tables created successfully!")

