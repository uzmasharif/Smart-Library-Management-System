

from flask import Flask, render_template, request, redirect, url_for, session, flash
from database.db import get_db_connection, create_tables
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from recommendation import recommend_books
import os
from dotenv import load_dotenv
from flask_wtf.csrf import CSRFProtect
import sqlite3

load_dotenv()

app = Flask(__name__)

app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")

if not app.config["SECRET_KEY"]:
    raise RuntimeError("SECRET_KEY is missing from .env file")
# Session Security
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax"
)
csrf = CSRFProtect(app)
create_tables()
def login_required(view_function):
    @wraps(view_function)
    def wrapped_view(*args, **kwargs):

        if "user_id" not in session:
            return redirect(url_for("login"))

        if session.get("role") != "admin":
            session.clear()
            return redirect(url_for("login"))

        return view_function(*args, **kwargs)

    return wrapped_view
def student_required(view_function):
    @wraps(view_function)
    def wrapped_view(*args, **kwargs):

        if "user_id" not in session:
            return redirect(url_for("login"))

        if session.get("role") != "student":
            return redirect(url_for("home"))

        return view_function(*args, **kwargs)

    return wrapped_view

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form["username"].strip()
        password = request.form["password"]

        connection = get_db_connection()

        user = connection.execute(
            "SELECT * FROM users WHERE username = ?",
            (username,)
        ).fetchone()

        connection.close()

        if user and check_password_hash(user["password"], password):
            session.clear()
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["role"] = user["role"]
            session["email"] = user["email"]

            if user["role"] == "admin":
                return redirect(url_for("home"))
            else:
                return redirect(url_for("student_dashboard"))

        return render_template(
            "login.html",
            error="Invalid username or password"
        )

    return render_template("login.html")


@app.route("/")
@login_required
def home():

    connection = get_db_connection()

    total_books = connection.execute(
        "SELECT COUNT(*) AS total FROM books"
    ).fetchone()["total"]

    total_students = connection.execute(
        "SELECT COUNT(*) AS total FROM students"
    ).fetchone()["total"]

    issued_books = connection.execute(
        "SELECT COUNT(*) AS total FROM borrow_records WHERE status = 'Borrowed'"
    ).fetchone()["total"]

    overdue_books = connection.execute(
        """SELECT COUNT(*) AS total
           FROM borrow_records
           WHERE status = 'Borrowed'
           AND due_date < date('now')"""
    ).fetchone()["total"]

    available_books = connection.execute(
        "SELECT COALESCE(SUM(quantity), 0) AS total FROM books"
    ).fetchone()["total"]

    connection.close()

    return render_template(
        "index.html",
        total_books=total_books,
        total_students=total_students,
        issued_books=issued_books,
        overdue_books=overdue_books,
        available_books=available_books
    )



# Student Dashboard
@app.route("/student-dashboard")
@student_required
def student_dashboard():

    search_query = request.args.get("search", "").strip()

    connection = get_db_connection()

    if search_query:
        available_books = connection.execute(
            """
            SELECT * FROM books
            WHERE quantity > 0
            AND (
                title LIKE ?
                OR author LIKE ?
                OR category LIKE ?
            )
            """,
            (
                f"%{search_query}%",
                f"%{search_query}%",
                f"%{search_query}%"
            )
        ).fetchall()

    else:
        available_books = connection.execute(
            "SELECT * FROM books WHERE quantity > 0"
        ).fetchall()

    connection.close()

    return render_template(
        "student_dashboard.html",
        available_books=available_books,
        search_query=search_query
    )


# My Borrowed Books
@app.route("/my-borrowed-books")
@student_required
def my_borrowed_books():

    connection = get_db_connection()

    borrowed_books = connection.execute(
        """
        SELECT
            borrow_records.id,
            books.title,
            books.author,
            borrow_records.borrow_date,
            borrow_records.due_date,
            borrow_records.return_date,
            borrow_records.status
        FROM borrow_records
        JOIN books
            ON borrow_records.book_id = books.id
        JOIN students
            ON borrow_records.student_id = students.id
        WHERE students.email = ?
        ORDER BY borrow_records.id DESC
        """,
        (session["email"],)
    ).fetchall()

    connection.close()

    return render_template(
        "my_borrowed_books.html",
        borrowed_books=borrowed_books
    )

# AI Book Recommendation
@app.route("/recommend-books", methods=["GET", "POST"])
@student_required
def recommend_books_page():

    recommendations = []
    topic = ""

    if request.method == "POST":

        topic = request.form.get("topic", "").strip()

        if topic:

            connection = get_db_connection()

            available_books = connection.execute(
                "SELECT * FROM books WHERE quantity > 0"
            ).fetchall()

            connection.close()

            recommendations = recommend_books(
                topic,
                available_books
            )

    return render_template(
        "recommendations.html",
        recommendations=recommendations,
        topic=topic
    )



@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        name = request.form["name"].strip()
        roll_no = request.form["roll_no"].strip()
        department = request.form["department"].strip()
        semester = request.form["semester"]
        email = request.form["email"].strip()
        username = request.form["username"].strip()
        password = request.form["password"]

        if len(password) < 8:
            return render_template(
                "register.html",
                error="Password must be at least 8 characters long."
            )

        hashed_password = generate_password_hash(password)

        connection = get_db_connection()

        try:

            connection.execute(
                """INSERT INTO students
                   (name, roll_no, department, semester, email)
                   VALUES (?, ?, ?, ?, ?)""",
                (name, roll_no, department, semester, email)
            )

            connection.execute(
                """INSERT INTO users
                   (username, email, password, role)
                   VALUES (?, ?, ?, ?)""",
                (username, email, hashed_password, "student")
            )

            connection.commit()
            connection.close()

            return redirect(url_for("login"))

        except sqlite3.IntegrityError:

            connection.rollback()
            connection.close()

            return render_template(
                "register.html",
                error="Username, email or roll number already exists."
            )

    return render_template("register.html")


@app.route("/logout", methods=["POST"])
def logout():

    session.clear()

    return redirect(url_for("login"))




@app.route("/books")
@login_required
def books():

    search_query = request.args.get("search", "")

    connection = get_db_connection()

    if search_query:

        all_books = connection.execute(
            """SELECT * FROM books
               WHERE title LIKE ?
               OR author LIKE ?
               OR category LIKE ?
               ORDER BY id DESC""",
            (
                f"%{search_query}%",
                f"%{search_query}%",
                f"%{search_query}%"
            )
        ).fetchall()

    else:

        all_books = connection.execute(
            "SELECT * FROM books ORDER BY id DESC"
        ).fetchall()

    connection.close()

    return render_template(
        "books.html",
        books=all_books,
        search_query=search_query
    )



@app.route("/add-book", methods=["POST"])
@login_required
def add_book():
    title = request.form["title"]
    author = request.form["author"]
    category = request.form["category"]
    quantity = request.form["quantity"]

    connection = get_db_connection()

    connection.execute(
        "INSERT INTO books (title, author, category, quantity) VALUES (?, ?, ?, ?)",
        (title, author, category, quantity)
    )

    connection.commit()
    connection.close()

    return redirect(url_for("books"))

@app.route("/delete-book/<int:book_id>", methods=["POST"])
@login_required
def delete_book(book_id):   


    connection = get_db_connection()

    connection.execute(
        "DELETE FROM books WHERE id = ?",
        (book_id,)
    )

    connection.commit()
    connection.close()

    return redirect(url_for("books"))


@app.route("/edit-book/<int:book_id>", methods=["GET", "POST"])
@login_required
def edit_book(book_id):

    connection = get_db_connection()

    if request.method == "POST":

        title = request.form["title"]
        author = request.form["author"]
        category = request.form["category"]
        quantity = request.form["quantity"]

        connection.execute(
            """UPDATE books
               SET title=?, author=?, category=?, quantity=?
               WHERE id=?""",
            (title, author, category, quantity, book_id)
        )

        connection.commit()
        connection.close()

        return redirect(url_for("books"))

    book = connection.execute(
        "SELECT * FROM books WHERE id=?",
        (book_id,)
    ).fetchone()

    connection.close()

    return render_template("edit_book.html", book=book)


@app.route("/students")
@login_required
def students():

    search_query = request.args.get("search", "")

    connection = get_db_connection()

    if search_query:

        all_students = connection.execute(
            """SELECT * FROM students
               WHERE name LIKE ?
               OR roll_no LIKE ?
               OR department LIKE ?
               ORDER BY id DESC""",
            (
                f"%{search_query}%",
                f"%{search_query}%",
                f"%{search_query}%"
            )
        ).fetchall()

    else:

        all_students = connection.execute(
            "SELECT * FROM students ORDER BY id DESC"
        ).fetchall()

    connection.close()

    return render_template(
        "students.html",
        students=all_students,
        search_query=search_query
    )



@app.route("/add-student", methods=["POST"])
@login_required
def add_student():

    name = request.form["name"]
    roll_no = request.form["roll_no"]
    department = request.form["department"]
    semester = request.form["semester"]
    email = request.form["email"]

    connection = get_db_connection()

    connection.execute(
        """INSERT INTO students
           (name, roll_no, department, semester, email)
           VALUES (?, ?, ?, ?, ?)""",
        (name, roll_no, department, semester, email)
    )

    connection.commit()
    connection.close()

    return redirect(url_for("students"))

@app.route("/delete-student/<int:student_id>", methods=["POST"])
@login_required
def delete_student(student_id):

    connection = get_db_connection()

    connection.execute(
        "DELETE FROM students WHERE id = ?",
        (student_id,)
    )

    connection.commit()
    connection.close()

    return redirect(url_for("students"))

@app.route("/edit-student/<int:student_id>", methods=["GET", "POST"])
@login_required
def edit_student(student_id):

    connection = get_db_connection()

    if request.method == "POST":

        name = request.form["name"]
        roll_no = request.form["roll_no"]
        department = request.form["department"]
        semester = request.form["semester"]
        email = request.form["email"]

        connection.execute(
            """UPDATE students
               SET name=?, roll_no=?, department=?,
                   semester=?, email=?
               WHERE id=?""",
            (name, roll_no, department, semester, email, student_id)
        )

        connection.commit()
        connection.close()

        return redirect(url_for("students"))

    student = connection.execute(
        "SELECT * FROM students WHERE id=?",
        (student_id,)
    ).fetchone()

    connection.close()

    return render_template("edit_student.html", student=student)


@app.route("/borrow")
@login_required
def borrow():

    connection = get_db_connection()

    all_students = connection.execute(
        "SELECT * FROM students ORDER BY name"
    ).fetchall()

    all_books = connection.execute(
        "SELECT * FROM books WHERE quantity > 0 ORDER BY title"
    ).fetchall()

    borrow_records = connection.execute(
        """SELECT borrow_records.*,
                  students.name AS student_name,
                  students.roll_no,
                  books.title AS book_title
           FROM borrow_records
           JOIN students ON borrow_records.student_id = students.id
           JOIN books ON borrow_records.book_id = books.id
           ORDER BY borrow_records.id DESC"""
    ).fetchall()
    overdue_records = connection.execute(
        """SELECT borrow_records.*,
                  students.name AS student_name,
                  students.roll_no,
                  books.title AS book_title
           FROM borrow_records
           JOIN students ON borrow_records.student_id = students.id
           JOIN books ON borrow_records.book_id = books.id
           WHERE borrow_records.status = 'Borrowed'
           AND borrow_records.due_date < date('now')
           ORDER BY borrow_records.due_date ASC"""
    ).fetchall()
    connection.close()

    return render_template(
        "borrow.html",
        students=all_students,
        books=all_books,
        borrow_records=borrow_records,
        overdue_records=overdue_records
    )


@app.route("/borrow-book", methods=["POST"])
@login_required
def borrow_book():

    student_id = request.form["student_id"]
    book_id = request.form["book_id"]
    borrow_date = request.form["borrow_date"]
    due_date = request.form["due_date"]

    from datetime import datetime

    try:
        borrow = datetime.strptime(borrow_date, "%Y-%m-%d")
        due = datetime.strptime(due_date, "%Y-%m-%d")
    except ValueError:
        return "Invalid date format!", 400

    if due <= borrow:
        return "Due date must be after borrow date!", 400

    connection = get_db_connection()

    student = connection.execute(
        "SELECT id FROM students WHERE id = ?",
        (student_id,)
    ).fetchone()

    book = connection.execute(
        "SELECT quantity FROM books WHERE id = ?",
        (book_id,)
    ).fetchone()

    if student is None or book is None:
        connection.close()
        return "Invalid student or book!", 400

    if book["quantity"] <= 0:
        connection.close()
        return "This book is not available!", 400

    connection.execute(
        """INSERT INTO borrow_records
           (student_id, book_id, borrow_date, due_date, status)
           VALUES (?, ?, ?, ?, 'Borrowed')""",
        (student_id, book_id, borrow_date, due_date)
    )

    connection.execute(
        "UPDATE books SET quantity = quantity - 1 WHERE id = ?",
        (book_id,)
    )

    connection.commit()
    connection.close()

    return redirect(url_for("borrow"))

@app.route("/return-book/<int:record_id>", methods=["POST"])
@login_required
def return_book(record_id):

    from datetime import date

    connection = get_db_connection()

    record = connection.execute(
        """SELECT * FROM borrow_records
           WHERE id = ? AND status = 'Borrowed'""",
        (record_id,)
    ).fetchone()

    if record is None:
        connection.close()
        return "Book already returned or record not found!", 400

    connection.execute(
        """UPDATE borrow_records
           SET status = 'Returned', return_date = ?
           WHERE id = ?""",
        (date.today().isoformat(), record_id)
    )

    connection.execute(
        "UPDATE books SET quantity = quantity + 1 WHERE id = ?",
        (record["book_id"],)
    )

    connection.commit()
    connection.close()

    return redirect(url_for("borrow"))
@app.route("/availability")
@login_required
def availability():

    connection = get_db_connection()

    all_books = connection.execute(
        """SELECT *
           FROM books
           ORDER BY title"""
    ).fetchall()

    connection.close()

    return render_template(
        "availability.html",
        books=all_books
    )
    
@app.route("/overdue")
@login_required
def overdue():

    connection = get_db_connection()

    overdue_records = connection.execute(
        """SELECT borrow_records.*,
                  students.name AS student_name,
                  students.roll_no,
                  books.title AS book_title
           FROM borrow_records
           JOIN students ON borrow_records.student_id = students.id
           JOIN books ON borrow_records.book_id = books.id
           WHERE borrow_records.status = 'Borrowed'
           AND borrow_records.due_date < date('now')
           ORDER BY borrow_records.due_date ASC"""
    ).fetchall()

    connection.close()

    return render_template(
        "overdue.html",
        overdue_records=overdue_records
    )

@app.route("/reports")
@login_required
def reports():

    connection = get_db_connection()

    total_books = connection.execute(
        "SELECT COUNT(*) AS total FROM books"
    ).fetchone()["total"]

    total_students = connection.execute(
        "SELECT COUNT(*) AS total FROM students"
    ).fetchone()["total"]

    issued_books = connection.execute(
        "SELECT COUNT(*) AS total FROM borrow_records WHERE status = 'Borrowed'"
    ).fetchone()["total"]

    returned_books = connection.execute(
        "SELECT COUNT(*) AS total FROM borrow_records WHERE status = 'Returned'"
    ).fetchone()["total"]

    overdue_books = connection.execute(
        """SELECT COUNT(*) AS total
           FROM borrow_records
           WHERE status = 'Borrowed'
           AND due_date < date('now')"""
    ).fetchone()["total"]

    available_copies = connection.execute(
        "SELECT COALESCE(SUM(quantity), 0) AS total FROM books"
    ).fetchone()["total"]

    connection.close()

    return render_template(
        "reports.html",
        total_books=total_books,
        total_students=total_students,
        issued_books=issued_books,
        returned_books=returned_books,
        overdue_books=overdue_books,
        available_copies=available_copies
    )

if __name__ == "__main__":
    app.run(debug=True)



