
import sqlite3
import os

# Project folder ka correct path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Database folder ka path
DATABASE_PATH = os.path.join(BASE_DIR, "database", "library.db")


def get_db_connection():

    connection = sqlite3.connect(DATABASE_PATH)

    # Database rows ko dictionary-style access dena
    connection.row_factory = sqlite3.Row

    # Foreign keys ko enforce karna
    connection.execute("PRAGMA foreign_keys = ON")

    return connection


def create_tables():

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

