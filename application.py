import os
import requests

from flask import Flask, render_template, request, session, flash
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


@app.route("/")
def index():
    if not session.get('logged_in'):
        return render_template('login.html')
    else:
        return render_template("index.html")

@app.route('/register', methods=['GET','POST'])
def register():
    if session.get('logged_in'):
        flash("You're already logged in. Please log out.")
        return render_template("index.html")
    else:
        if request.method == 'POST':

            # Get form information.
            username = str(request.form.get("username")) or None
            email = str(request.form.get("email")) or None
            password = str(request.form.get("password")) or None

            user = db.execute("SELECT * FROM users WHERE LOWER(name) = LOWER(:username)",
                {"username": username}).fetchone()

            if user:
                flash("You're already in our system. Please login.")
                return render_template("login.html")
            elif all(v is not None for v in [username, email, password]):
                db.execute("INSERT INTO users (name, email, password) VALUES (:username, :email, :password)",
                {"username": username, "email": email, "password": password})
                db.commit()
                logged_in = db.execute("SELECT * FROM users WHERE LOWER(name) = LOWER(:username)",
                    {"username": username}).fetchone()
                session['logged_in'] = True
                session['user_id'] = logged_in[0]
                session['user_name'] = logged_in[1]
                #redirect to home
                flash("Registration Successful. Your are logged in.")
                return render_template("index.html")
            else:
                flash("Please correct data")
                return render_template("register.html")
        else:
            return render_template("register.html")

@app.route('/login', methods=['GET','POST'])
def login():
    if session.get('logged_in'):
        flash("You're already logged in. Please log out.")
        return render_template("index.html")
    else:
        if request.method == 'POST':
            username = str(request.form.get("username"))
            password = str(request.form.get("password"))
            logged_in = db.execute("SELECT * FROM users WHERE LOWER(name) = LOWER(:username) AND  password = :password",
                    {"username": username, "password": password}).fetchone()

            if logged_in:
                session['logged_in'] = True
                session['user_id'] = logged_in[0]
                session['user_name'] = logged_in[1]
            else:
                 flash("Please try again or register.")
                 return render_template("login.html")
            return render_template("index.html")
        else:
            return render_template("login.html")

@app.route("/logout")
def logout():
    session['logged_in'] = False
    return index()

@app.route("/delete_user", methods=['POST'])
def delete_user():
    user_to_delete = str(request.form.get("user_to_delete"))
    db.execute("DELETE FROM users WHERE name = :user_to_delete",
        {"user_to_delete": user_to_delete})
    db.commit()
    return admin()

@app.route("/books", methods=['GET', 'POST'])
def books():
    if not session.get('logged_in'):
        return render_template('login.html')
    else:
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
    if not session.get('logged_in'):
        return render_template('login.html')
    else:

        res = requests.get("https://www.goodreads.com/book/review_counts.json",
                        params={"key": "GtG9odDoZNEWxekOhsmMA", "isbns": book_isbn})
        if res.status_code != 200:
            raise Exception("ERROR: API request unsuccessful.")
        data = res.json()

        ratings_count = data["books"][0]["ratings_count"]
        average_rating = data["books"][0]["average_rating"]

        reviews = db.execute("SELECT * FROM reviews").fetchall()

        # Make sure book exists.
        book = db.execute("SELECT * FROM books WHERE isbn = :isbn", {"isbn": book_isbn}).fetchone()
        if book is None:
            return render_template("error.html", message="No such book.")

        user_name = db.execute("SELECT name FROM users JOIN reviews ON reviews.user_id = users.id;").fetchone()
        return render_template("book.html", book=book, ratings_count=ratings_count, average_rating=average_rating, reviews=reviews, user_name=user_name)

@app.route("/review", methods=["POST"])
def review():
    if not session.get('logged_in'):
        return render_template('login.html')
    else:
        # Get form information.
        rating = request.form.get("rating")
        content = request.form.get("content")
        isbn = request.form.get("isbn")
        user_id = session.get('user_id')

        book = db.execute("SELECT * FROM books WHERE isbn = :isbn", {"isbn": isbn}).fetchone()

        # if not book:
        #     flash("No such book.")
        #     return render_template("error.html")
        # elif all(v is not None for v in [username, email, password]):
        #     db.execute("INSERT INTO users (name, email, password) VALUES (:username, :email, :password)",
        #     {"username": username, "email": email, "password": password})
        #     db.commit()
        #     logged_in = db.execute("SELECT * FROM users WHERE LOWER(name) = LOWER(:username)",
        #         {"username": username}).fetchone()
        #     session['logged_in'] = True
        #     session['user_id'] = logged_in[0]
        #     session['user_name'] = logged_in[1]
        #     #redirect to home
        #     flash("Registration Successful. Your are logged in.")
        #     return render_template("index.html")
        # else:
        #     flash("Please correct data")
        #     return render_template("register.html")
        # Make sure the book exists.
        if db.execute("SELECT * FROM books WHERE isbn = :isbn", {"isbn": isbn}).rowcount == 0:
            flash("You're already logged in. Please log out.")
            return render_template("index.html")
          return render_template("error.html", message="No such book with that isbn.")
        db.execute("INSERT INTO reviews (rating, content, date, isbn, user_id) VALUES (:rating, :content, current_timestamp, :isbn, :user_id)",
              {"rating": rating, "content": content, "isbn": isbn, "user_id": user_id})
        db.commit()
        return book(isbn)

@app.route("/delete_review", methods=["POST"])
def delete_review():
    if not session.get('logged_in'):
        return render_template('login.html')
    else:
        book_isbn = str(request.form.get("book_isbn"))
        user_id = session.get('user_id')

        db.execute("DELETE FROM reviews WHERE user_id = :user_id AND isbn = :isbn",
            {"user_id": user_id, "isbn": book_isbn})
        db.commit()
        return render_template("success.html")

@app.route("/admin", methods=['GET', 'POST'])
def admin():
    if not session.get('logged_in'):
        return render_template('login.html')
    else:
        if request.method == 'POST':
            # Get form information.
            username = request.form.get("username") or None
            email = request.form.get("email") or None
            password = request.form.get("password") or None

            print(username, email, password)

            if all(v is not None for v in [username, email, password]):
                db.execute("INSERT INTO users (name, email, password) VALUES (:username, :email, :password)",
                {"username": username, "email": email, "password": password})
                db.commit()
                users = db.execute("SELECT * FROM users").fetchall()
                return render_template("admin.html", users=users)
            else:
                message = "No empty field"
                users = db.execute("SELECT * FROM users").fetchall()
                return render_template("admin.html", users=users, message=message)
        else:
            users = db.execute("SELECT * FROM users").fetchall()
            return render_template("admin.html", users=users)
