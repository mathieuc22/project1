import os
import requests
import math

from flask import Flask, render_template, request, session, flash, redirect, url_for,jsonify
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
            # Get form information
            username = str(request.form.get("username")) or None
            email = str(request.form.get("email")) or None
            password = str(request.form.get("password")) or None
            # Check if user exists
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
                # Store info on the session
                session['logged_in'] = logged_in
                session['user_id'] = logged_in.id
                session['user_name'] = logged_in.name
                session['user_isadmin'] = logged_in.isadmin
                # Redirect to home
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
            # Get form information
            username = str(request.form.get("username")) or None
            password = str(request.form.get("password")) or None
            # Check if info are good
            logged_in = db.execute("SELECT * FROM users WHERE LOWER(name) = LOWER(:username) AND  password = :password",
                    {"username": username, "password": password}).fetchone()
            if logged_in:
                session['logged_in'] = logged_in
                session['user_id'] = logged_in.id
                session['user_name'] = logged_in.name
                session['user_isadmin'] = logged_in.isadmin
                return redirect(url_for('index'))
            else:
                 flash("Please try again or register.")
                 return render_template("login.html")
        else:
            return redirect(url_for('index'))

@app.route("/logout")
def logout():
    session['logged_in'] = False
    return redirect(url_for('login'))

@app.route("/delete_user", methods=['POST'])
def delete_user():
    user_id = request.args.get('user_id')
    db.execute("DELETE FROM users WHERE id = :user_id",
        {"user_id": user_id})
    db.commit()
    return redirect(url_for('users'))

@app.route("/books", methods=['GET', 'POST'])
@app.route("/books/<int:page>", methods=['GET', 'POST'])
def books(page=1):
    if not session.get('logged_in'):
        return render_template('login.html')
    else:
        # Pagination
        perpage=100
        startat=page*perpage-perpage
        # Handle a search session storage
        if request.method == 'POST':
            search = request.form.get("search")
            session['search'] = search
        else:
            search = session.get('search')
        # Search SQL
        books = db.execute("SELECT * FROM books WHERE LOWER(title) LIKE LOWER(:search) OR  LOWER(author) LIKE LOWER(:search) OR  LOWER(isbn) LIKE LOWER(:search) OR  CAST(year AS TEXT) LIKE :search ORDER BY isbn LIMIT :perpage OFFSET :startat",
                {"search": '%'+search+'%', "perpage": perpage, "startat": startat}).fetchall()
        # Count SQL
        count = db.execute("SELECT count(*) as nb FROM books WHERE LOWER(title) LIKE LOWER(:search) OR  LOWER(author) LIKE LOWER(:search) OR  LOWER(isbn) LIKE LOWER(:search) OR  CAST(year AS TEXT) LIKE :search",
                {"search": '%'+search+'%'}).fetchone()
        nb_books = count.nb
        # Check if books are returned
        if nb_books == 0:
            nb_pages = 0
            message = 'No book found'
        else:
            nb_pages = math.ceil(nb_books/perpage)
            message = f'Found {nb_books} book(s)'
        return render_template("books.html",
                books=books,
                search=search,
                message=message,
                nb_pages=nb_pages,
                page=page
                )

@app.route("/books/author/<string:author>")
def author(author):
    if not session.get('logged_in'):
        return render_template('login.html')
    else:
        session['search'] = author
        return redirect(url_for('books'))

@app.route("/books/year/<int:year>")
def year(year):
    if not session.get('logged_in'):
        return render_template('login.html')
    else:
        session['search'] = str(year)
        return redirect(url_for('books'))

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
        try:
            description = gdata["items"][0]["volumeInfo"]["description"]
            language = gdata["items"][0]["volumeInfo"]["language"]
        except KeyError:
            description=""
            language=""
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
            # Get form information
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
        # Render the book page
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
        if all(v is not None for v in [book_isbn, user_id]):
            db.execute("DELETE FROM reviews WHERE user_id = :user_id AND isbn = :isbn",
                {"user_id": user_id, "isbn": book_isbn})
            db.commit()
            return redirect(url_for('book', book_isbn=book_isbn))
        else:
            return render_template("error.html", message="Please check your review.")

@app.route("/review/<int:review_id>", methods=["GET", "POST"])
def update_review(review_id):
    if not session.get('logged_in'):
        return render_template('login.html')
    else:
        # Make sure review exists.
        review = db.execute("SELECT * FROM reviews WHERE id = :id", {"id": review_id}).fetchone()
        if review is None:
            return render_template("error.html", message="No such review.")
        # Get the isbn and user
        book_isbn = review.isbn
        user_id = session.get('user_id')
        # Check if the user can update the review
        if user_id != review.user_id:
            return render_template("error.html", message="Not your review.")
        # Update the review
        elif request.method == 'POST':
            rating = request.form.get("rating") or None
            content = request.form.get("content") or None
            if all(v is not None for v in [rating, content]):
                db.execute("UPDATE reviews SET date = current_timestamp, rating = :rating, content = :content WHERE user_id = :user_id AND isbn = :isbn",
                    {"rating": rating, "content": content, "user_id": user_id, "isbn": book_isbn})
                db.commit()
                return redirect(url_for('book', book_isbn=book_isbn))
            else:
                flash("Please add rating and content.")
        else:
            review = db.execute("SELECT reviews.id, reviews.date, reviews.rating, reviews.isbn, reviews.content, books.title, users.name FROM reviews JOIN books ON books.isbn = reviews.isbn JOIN users ON users.id = reviews.user_id WHERE reviews.id = :review_id AND reviews.user_id = :user_id", {"review_id": review_id, "user_id": user_id}).fetchone()
        return render_template('update_review.html', review=review)

# List reviews (For admin only)
@app.route("/reviews")
def reviews():
    if not session.get('logged_in'):
        return render_template('login.html')
    else:
        reviews = db.execute("SELECT reviews.id, to_char(reviews.date, 'DD/MM/YY') as date, reviews.rating, reviews.content, reviews.user_id, users.name, books.title,  books.isbn FROM reviews JOIN users ON users.id = reviews.user_id JOIN books ON books.isbn = reviews.isbn").fetchall()
        # Check if reviews exist
        if reviews:
            nb_reviews = len(reviews) or None
            message = f'Found {nb_reviews} reviews'
            return render_template("reviews.html", message=message, reviews=reviews)
        else:
            return render_template("error.html", message="No review for this user.")

# List reviews by user (For admin only)
@app.route("/reviews/<int:user_id>")
def reviews_by_user(user_id):
    if not session.get('logged_in'):
        return render_template('login.html')
    else:
        reviews = db.execute("SELECT reviews.id, to_char(reviews.date, 'DD/MM/YY') as date, reviews.rating, reviews.content, reviews.user_id, users.name, books.title,  books.isbn FROM reviews JOIN users ON users.id = reviews.user_id JOIN books ON books.isbn = reviews.isbn WHERE reviews.user_id = :user_id", {"user_id": user_id}).fetchall()
         # Check if reviews exist
        if reviews:
            username = db.execute("SELECT users.name FROM users JOIN reviews ON users.id = reviews.user_id WHERE reviews.user_id = :user_id", {"user_id": user_id}).fetchone()
            nb_reviews = len(reviews) or None
            message = f'Found {nb_reviews} reviews'
            return render_template("reviews.html", username=username.name, message=message, reviews=reviews)
        else:
            return render_template("error.html", message="No review for this user.")

# List users (For admin only)
@app.route("/users", methods=['GET', 'POST'])
def users():
    if not session.get('logged_in'):
        return render_template('login.html')
    elif not session.get('user_isadmin'):
        return render_template('error.html', message='For admin users only')
    else:
        # Create a new user
        if request.method == 'POST':
            # Get form information.
            username = str(request.form.get("username")) or None
            email = str(request.form.get("email")) or None
            password = str(request.form.get("password")) or None
            # Validation
            if all(v is not None for v in [username, email, password]):
                db.execute("INSERT INTO users (name, email, password) VALUES (:username, :email, :password)",
                {"username": username, "email": email, "password": password})
                db.commit()
            else:
                flash("No empty field")
        # List the users
        users = db.execute("SELECT * FROM users").fetchall()
        nb_users = len(users)
        message = f'Found {nb_users} users'
        return render_template("users.html", users=users, message=message)

@app.route("/user/<int:user_id>", methods=['GET', 'POST'])
def profile(user_id):
    if not session.get('logged_in'):
        return render_template('login.html')
    else:
        # Only display user's profile
        current_user_id = session.get("user_id") or None
        if user_id != current_user_id:
            return render_template("error.html", message="Not you.")
        # Get the users reviews
        reviews = db.execute("SELECT reviews.id, to_char(reviews.date, 'DD/MM/YY') as date, reviews.rating, reviews.content, reviews.user_id, users.name, books.title,  books.isbn FROM reviews JOIN users ON users.id = reviews.user_id JOIN books ON books.isbn = reviews.isbn WHERE reviews.user_id = :user_id",
                {"user_id": user_id}).fetchall()
        # User can update infos
        if request.method == 'POST':
            username = request.form.get("username") or None
            email = request.form.get("email") or None
            password = request.form.get("password") or None
            # Validation
            if all(v is not None for v in [username, email, password]):
                db.execute("UPDATE users SET name = :username, email = :email, password = :password WHERE id = :user_id",
                    {"username": username, "email": email, "password": password, "user_id": user_id})
                db.commit()
                flash("You've updated your infos")
            else:
                flash("No empty field")
        # Get user info
        user = db.execute("SELECT * FROM users WHERE id = :user_id", {"user_id": user_id}).fetchone()
        return render_template("profile.html", user=user, reviews=reviews)

@app.route("/api/<string:book_isbn>")
def api(book_isbn):
    # Retrieve infos
    book = db.execute("SELECT * FROM books WHERE isbn = :book_isbn",
            {"book_isbn": book_isbn}).fetchone()
    # Check if book exists in the db
    if book is None:
        # return jsonify({"error": "Invalid ISBN"}), 422
        return render_template("error.html", message="No such book.")
    # Get reviews from goodread API
    res = requests.get("https://www.goodreads.com/book/review_counts.json",
                    params={"key": "GtG9odDoZNEWxekOhsmMA", "isbns": book_isbn})
    if res.status_code != 200:
        raise Exception("ERROR: API request unsuccessful.")
    data = res.json()
    ratings_count = data["books"][0]["ratings_count"]
    average_rating = data["books"][0]["average_rating"]
    # Make the return
    return jsonify({
            "title": book.title,
            "author": book.author,
            "year": book.year,
            "isbn": book.isbn,
            "review_count": average_rating,
            "average_score": ratings_count
        })
