import os
import requests

from flask import Flask, render_template, request, session, flash, redirect, url_for
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
                session['logged_in'] = logged_in
                session['user_id'] = logged_in.id
                session['user_name'] = logged_in.name
                session['user_isadmin'] = logged_in.isadmin
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
                session['logged_in'] = logged_in
                session['user_id'] = logged_in.id
                session['user_name'] = logged_in.name
                session['user_isadmin'] = logged_in.isadmin
            else:
                 flash("Please try again or register.")
                 return render_template("login.html")
            return redirect(url_for('index'))
        else:
            return redirect(url_for('index'))

@app.route("/logout")
def logout():
    session['logged_in'] = False
    return redirect(url_for('login'))

@app.route("/delete_user", methods=['POST'])
def delete_user():
    user_to_delete = str(request.form.get("user_to_delete"))
    db.execute("DELETE FROM users WHERE name = :user_to_delete",
        {"user_to_delete": user_to_delete})
    db.commit()
    return redirect(url_for('users'))

@app.route("/books", methods=['GET', 'POST'])
def books():
    if not session.get('logged_in'):
        return render_template('login.html')
    else:
        if request.method == 'POST':
            search = request.form.get("search")
            print(search)

            # Search SQL
            books = db.execute("SELECT * FROM books WHERE LOWER(title) LIKE LOWER(:search) OR  LOWER(author) LIKE LOWER(:search) OR  LOWER(isbn) LIKE LOWER(:search) OR  CAST(year AS TEXT) LIKE :search",
                    {"search": '%'+search+'%'}).fetchall()
            nb_books = len(books)

            session['books'] = books

            if nb_books == 0:
                message = 'No book found'
            else:
                message = f'Found {nb_books} book(s)'
            return render_template("books.html", books=books, search=search, message=message)
        else:
            books = session.get('books') or None
            if books is None:
                books = db.execute("SELECT * FROM books").fetchall()
            nb_books = len(books)
            message = f'Found {nb_books} book(s)'
            return render_template("books.html", message=message, books=books)

@app.route("/book/<string:book_isbn>", methods=["GET", "POST"])
def book(book_isbn):
    if not session.get('logged_in'):
        return render_template('login.html')
    else:

        # Make sure book exists.
        book = db.execute("SELECT * FROM books WHERE isbn = :isbn", {"isbn": book_isbn}).fetchone()
        if book is None:
            return render_template("error.html", message="No such book.")

        # Get reviews from googleapis
        gapi = requests.get("https://www.googleapis.com/books/v1/volumes",
                        params={"q": "isbn:"+book_isbn})
        if gapi.status_code != 200:
            raise Exception("ERROR: API request unsuccessful.")
        gdata = gapi.json()
        description = gdata["items"][0]["volumeInfo"]["description"]
        language = gdata["items"][0]["volumeInfo"]["language"]

        # Get reviews from goodread API
        res = requests.get("https://www.goodreads.com/book/review_counts.json",
                        params={"key": "GtG9odDoZNEWxekOhsmMA", "isbns": book_isbn})
        if res.status_code != 200:
            raise Exception("ERROR: API request unsuccessful.")
        data = res.json()
        ratings_count = data["books"][0]["ratings_count"]
        average_rating = data["books"][0]["average_rating"]

        # Get some usefull variables
        user_name = session.get('user_name') or None
        user_id = session.get('user_id') or None
        review_by_user = db.execute("SELECT * FROM reviews WHERE isbn = :isbn AND user_id = :user_id", {"isbn": book_isbn, "user_id": user_id}).fetchone()

        # Insert a new review
        if request.method == 'POST':
            # Get form information.
            rating = request.form.get("rating") or None
            content = request.form.get("content") or None
            if review_by_user:
                flash("You've reviewed this book already")
            elif all(v is not None for v in [rating, content, book_isbn, user_id]):
                db.execute("INSERT INTO reviews (rating, content, date, isbn, user_id) VALUES (:rating, :content, current_timestamp, :isbn, :user_id)",
                    {"rating": rating, "content": content, "isbn": book_isbn, "user_id": user_id})
                db.commit()
                review_by_user = True
            else:
                flash("Please correct data")

        # Get reviews for the book
        reviews = db.execute("SELECT reviews.id, to_char(reviews.date, 'DD/MM/YY') as date, reviews.rating, reviews.content, users.name FROM reviews JOIN users ON users.id = reviews.user_id WHERE isbn = :isbn", {"isbn": book_isbn}).fetchall()

        return render_template("book.html",
                        book=book,
                        reviews=reviews,
                        ratings_count=ratings_count,
                        average_rating=average_rating,
                        review_by_user=review_by_user,
                        user_name=user_name,
                        description=description,
                        language=language
                        )

@app.route("/delete_review", methods=["POST"])
def delete_review():
    if not session.get('logged_in'):
        return render_template('login.html')
    else:
        book_isbn = request.form.get("book_isbn") or None
        user_id = session.get('user_id')

        db.execute("DELETE FROM reviews WHERE user_id = :user_id AND isbn = :isbn",
            {"user_id": user_id, "isbn": book_isbn})
        db.commit()
        return redirect(url_for('book', book_isbn=book_isbn))

@app.route("/review/<int:review_id>", methods=["GET", "POST"])
def update_review(review_id):
    if not session.get('logged_in'):
        return render_template('login.html')
    else:
        user_id = session.get('user_id')
        if request.method == 'POST':
            book_isbn = request.form.get("isbn") or None
            rating = request.form.get("rating") or None
            content = request.form.get("content") or None

            db.execute("UPDATE reviews SET date = current_timestamp, rating = :rating, content = :content WHERE user_id = :user_id AND isbn = :isbn",
                {"rating": rating, "content": content, "user_id": user_id, "isbn": book_isbn})
            db.commit()
            return redirect(url_for('book', book_isbn=book_isbn))
        else:
            review = db.execute("SELECT reviews.id, reviews.date, reviews.rating, reviews.isbn, reviews.content, books.title FROM reviews JOIN books ON books.isbn = reviews.isbn WHERE id = :review_id AND user_id = :user_id", {"review_id": review_id, "user_id": user_id}).fetchone()
            return render_template('update_review.html', review=review)

@app.route("/books/author/<string:author>")
def author(author):
    if not session.get('logged_in'):
        return render_template('login.html')
    else:
        books = db.execute("SELECT * FROM books WHERE LOWER(author) = LOWER(:author)", {"author": author}).fetchall()
        nb_books = len(books)
        message = f'Found {nb_books} book(s)'
        return render_template("books.html", message=message, books=books)

@app.route("/books/year/<int:year>")
def year(year):
    if not session.get('logged_in'):
        return render_template('login.html')
    else:
        books = db.execute("SELECT * FROM books WHERE year = :year", {"year": year}).fetchall()
        nb_books = len(books)
        message = f'Found {nb_books} book(s)'
        return render_template("books.html", message=message, books=books)

@app.route("/reviews")
def reviews():
    if not session.get('logged_in'):
        return render_template('login.html')
    else:
        reviews = db.execute("SELECT reviews.id, to_char(reviews.date, 'DD/MM/YY') as date, reviews.rating, reviews.content, reviews.user_id, users.name, books.title,  books.isbn FROM reviews JOIN users ON users.id = reviews.user_id JOIN books ON books.isbn = reviews.isbn").fetchall()
        nb_reviews = len(reviews)
        message = f'Found {nb_reviews} reviews'
        return render_template("reviews.html", message=message, reviews=reviews)

@app.route("/reviews/<int:user_id>")
def reviews_by_user(user_id):
    if not session.get('logged_in'):
        return render_template('login.html')
    else:
        reviews = db.execute("SELECT reviews.id, to_char(reviews.date, 'DD/MM/YY') as date, reviews.rating, reviews.content, reviews.user_id, users.name, books.title,  books.isbn FROM reviews JOIN users ON users.id = reviews.user_id JOIN books ON books.isbn = reviews.isbn WHERE reviews.user_id = :user_id", {"user_id": user_id}).fetchall()
        username = db.execute("SELECT users.name FROM users JOIN reviews ON users.id = reviews.user_id WHERE reviews.user_id = :user_id", {"user_id": user_id}).fetchone()
        nb_reviews = len(reviews)
        message = f'Found {nb_reviews} reviews'
        return render_template("reviews.html", username=username.name, message=message, reviews=reviews)

@app.route("/users", methods=['GET', 'POST'])
def users():
    if not session.get('logged_in'):
        return render_template('login.html')
    elif not session.get('user_isadmin'):
        return render_template('error.html', message='For admin users only')
    else:
        if request.method == 'POST':
            # Get form information.
            username = str(request.form.get("username")) or None
            email = str(request.form.get("email")) or None
            password = str(request.form.get("password")) or None

            if all(v is not None for v in [username, email, password]):
                db.execute("INSERT INTO users (name, email, password) VALUES (:username, :email, :password)",
                {"username": username, "email": email, "password": password})
                db.commit()
                users = db.execute("SELECT * FROM users").fetchall()
                return render_template("users.html", users=users)
            else:
                message = "No empty field"
                users = db.execute("SELECT * FROM users").fetchall()
                return render_template("users.html", users=users, message=message)
        else:
            users = db.execute("SELECT * FROM users").fetchall()
            nb_users = len(users)
            message = f'Found {nb_users} users'
            return render_template("users.html", users=users, message=message)

@app.route("/profile")
def profile():
    if not session.get('logged_in'):
        return render_template('login.html')
    else:
        user_id = str(session.get("user_id")) or None

        user = db.execute("SELECT * FROM users WHERE id = :user_id", {"user_id": user_id}).fetchone()

        reviews = db.execute("SELECT reviews.id, to_char(reviews.date, 'DD/MM/YY') as date, reviews.rating, reviews.content, reviews.user_id, users.name, books.title,  books.isbn FROM reviews JOIN users ON users.id = reviews.user_id JOIN books ON books.isbn = reviews.isbn WHERE reviews.user_id = :user_id", {"user_id": user_id}).fetchall()

        return render_template("profile.html", user=user, reviews=reviews)
