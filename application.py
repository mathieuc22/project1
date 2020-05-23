import os

from flask import Flask, render_template, request, session
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

app = Flask(__name__)

# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))


@app.route("/", methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        date = request.form.get("date")
        if date == '':
            books = ''
            return render_template("index.html", books=books)

        books = db.execute("SELECT * FROM books WHERE year = :book_date",
                {"book_date": date}).fetchone()
        if books is None:
            return render_template("error.html", message="No such book.")


        books = db.execute("SELECT * FROM books WHERE year = :book_date",
                {"book_date": date}).fetchall()
        return render_template("index.html", books=books)
    else:
        books = db.execute("SELECT * FROM books fetch first 10 rows only").fetchall()
        return render_template("index.html", books=books)

@app.route("/books", methods=['GET', 'POST'])
def books():
    if request.method == 'POST':
        date = request.form.get("date")
        if date == '':
            books = ''
            return render_template("books.html", books=books)

        books = db.execute("SELECT * FROM books WHERE year = :book_date",
                {"book_date": date}).fetchone()
        if books is None:
            return render_template("error.html", message="No such book.")


        books = db.execute("SELECT * FROM books WHERE year = :book_date",
                {"book_date": date}).fetchall()
        return render_template("books.html", books=books)
    else:
        books = db.execute("SELECT * FROM books fetch first 10 rows only").fetchall()
        return render_template("books.html", books=books)

@app.route("/books/<string:book_isbn>")
def book(book_isbn):
    """Lists details about a single book."""

    # Make sure flight exists.
    book = db.execute("SELECT * FROM books WHERE isbn = :isbn", {"isbn": book_isbn}).fetchone()
    if book is None:
        return render_template("error.html", message="No such book.")
    return render_template("book.html", book=book)
