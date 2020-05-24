import os
import requests

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
        search = '%'+request.form.get("search")+'%'

        # Search SQL
        books = db.execute("SELECT * FROM books WHERE title LIKE :search OR  author LIKE :search OR  isbn LIKE :search OR  CAST(year AS TEXT) LIKE :search",
                {"search": search}).fetchall()
        return render_template("index.html", books=books)
    else:
        books = db.execute("SELECT * FROM books fetch first 10 rows only").fetchall()
        return render_template("index.html", books=books)

@app.route("/books", methods=['GET', 'POST'])
def books():
    if request.method == 'POST':
        search = request.form.get("search")

        # Search SQL
        books = db.execute("SELECT * FROM books WHERE LOWER(title) LIKE LOWER(:search) OR  LOWER(author) LIKE LOWER(:search) OR  LOWER(isbn) LIKE LOWER(:search) OR  CAST(year AS TEXT) LIKE :search",
                {"search": '%'+search+'%'}).fetchall()
        nb_books = len(books)
        print(nb_books)
        if nb_books == 0:
            message = 'No book found'
        else:
            message = f'Found {nb_books} book(s)'
        return render_template("books.html", books=books, search=search, message=message)
    else:
        books = db.execute("SELECT * FROM books fetch first 10 rows only").fetchall()
        return render_template("books.html", books=books)

@app.route("/books/<string:book_isbn>")
def book(book_isbn):
    """Lists details about a single book."""

    res = requests.get("https://www.goodreads.com/book/review_counts.json",
                    params={"key": "GtG9odDoZNEWxekOhsmMA", "isbns": book_isbn})
    if res.status_code != 200:
        raise Exception("ERROR: API request unsuccessful.")
    data = res.json()

    ratings_count = data["books"][0]["ratings_count"]
    average_rating = data["books"][0]["average_rating"]

    users = db.execute("SELECT * FROM users").fetchall()
    reviews = db.execute("SELECT * FROM reviews").fetchall()

    # Make sure book exists.
    book = db.execute("SELECT * FROM books WHERE isbn = :isbn", {"isbn": book_isbn}).fetchone()
    if book is None:
        return render_template("error.html", message="No such book.")

    return render_template("book.html", book=book, book_isbn=book_isbn, ratings_count=ratings_count, average_rating=average_rating, users=users, reviews=reviews)

@app.route("/review", methods=["POST"])
def review():
    # Get form information.
    rating = request.form.get("rating")
    content = request.form.get("content")
    user = request.form.get("user")
    isbn = request.form.get("isbn")

    # Make sure the flight exists.
    if db.execute("SELECT * FROM books WHERE isbn = :isbn", {"isbn": isbn}).rowcount == 0:
      return render_template("error.html", message="No such book with that isbn.")
    db.execute("INSERT INTO reviews (rating, content, date, isbn, user_id) VALUES (:rating, :content, current_timestamp, :isbn, :user_id)",
          {"rating": rating, "content": content, "isbn": isbn, "user_id": user})
    db.commit()
    return render_template("success.html")

@app.route("/register", methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # Get form information.
        name = request.form.get("name")
        email = request.form.get("email")

        db.execute("INSERT INTO users (name, email) VALUES (:name, :email)",
        {"name": name, "email": email})
        db.commit()

        users = db.execute("SELECT * FROM users").fetchall()
        return render_template("register.html", users=users)
    else:
        users = db.execute("SELECT * FROM users").fetchall()
        return render_template("register.html", users=users)
