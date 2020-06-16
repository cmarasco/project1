import os

from flask import Flask, render_template, session, request, jsonify
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
import requests

#res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": "5EgIdTu1AvXOLH3FqL1xA", "isbns": "0803734964"})

app = Flask(__name__)

# Check for environment variable
#postgres://xuamwmjtjcyrfb:f807b646771b36230b52e1aa265d4e6bc863587b5694d7de940c3b2ae248c35d@ec2-52-87-135-240.compute-1.amazonaws.com:5432/dcpraqjb9jm2m8
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))

global current_user
current_user = None

@app.route("/", methods=['GET', 'POST'])
def login():
    global current_user
    current_user = None
    return render_template("login.html")

@app.route("/createaccount", methods=['GET', 'POST'])
def createaccount():
    return render_template("newaccount.html")

@app.route("/accountcreated", methods=["POST"])
def accountcreated():
    createusername = request.form.get("createusername")
    createpassword = request.form.get("createpassword")

    if (db.execute("SELECT * FROM users WHERE (name = :un)", {"un": createusername}).rowcount == 1):
        return render_template("newaccount.html", user_message="That username already exists.", pw_message="")
    elif (createusername == ""):
        return render_template("newaccount.html", user_message="Please enter a username.", pw_message="")
    elif (createpassword == ""):
        return render_template("newaccount.html", user_message="", pw_message="Please enter a password.")
    else:
        db.execute("INSERT INTO users (name, password) VALUES (:un, :pw)", {"un": createusername, "pw": createpassword})
        db.commit()
        return render_template("success.html", message="Account created!", head="Success!")

@app.route("/logout", methods=["POST"])
def logout():
    global current_user
    current_user = None
    return render_template("success.html", message="You have logged out", head="Success!")

@app.route("/search", methods=["POST"])
def search():
    username = request.form.get("username")
    password = request.form.get("password")

    if (db.execute("SELECT * FROM users WHERE (name = :un) AND (password = :pw)", {"un": username, "pw": password}).rowcount == 1):
        global current_user
        current_user = db.execute("SELECT * FROM users WHERE (name = :un) AND (password = :pw)", {"un": username, "pw": password}).fetchone().id
        return render_template("search.html")
    elif (db.execute("SELECT * FROM users WHERE (name = :un)", {"un": username}).rowcount == 0):
        return render_template("login.html", user_message="That username does not exist.", pw_message="")
    else:
        return render_template("login.html", user_message="", pw_message="The password does not match.")

@app.route("/books", methods=["POST"])
def books():
    global current_user
    if (current_user == None):
        return render_template("success.html", message="You are not logged in.", head="Error")

    booksearch = "%" + request.form.get("booksearch").lower() + "%"
    stars = []
    ratings = []

    # Get all passengers.
    books = db.execute("SELECT * FROM books WHERE LOWER(title) LIKE :booksearch", {"booksearch": booksearch}).fetchall()
    if (db.execute("SELECT * FROM books WHERE LOWER(author) LIKE :booksearch", {"booksearch": booksearch}).rowcount != 0):
        books.extend(db.execute("SELECT * FROM books WHERE LOWER(author) LIKE :booksearch", {"booksearch": booksearch}).fetchall())
    if (db.execute("SELECT * FROM books WHERE LOWER(ibsn) LIKE :booksearch", {"booksearch": booksearch}).rowcount != 0):
        books.extend(db.execute("SELECT * FROM books WHERE LOWER(ibsn) LIKE :booksearch", {"booksearch": booksearch}).fetchall())
    if len(books) == 0:
        message = "No books match that search"
    else:
        message = ""
        for i in range(0, len(books)):
            try:
                res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": "5EgIdTu1AvXOLH3FqL1xA", "isbns": books[i].ibsn}).json()
                rating = res['books'][0]['average_rating']
                ratings.append(rating)
                star = round(float(rating))
                stars.append(star)
            except:
                stars.append(0)
                ratings.append("Not available")
    return render_template("books.html", books=books, bookslen=len(books), message=message, ratings=ratings, stars=stars)

@app.route("/book/<int:book_id>", methods=["POST"])
def book(book_id):
    global current_user
    if current_user == None:
        return render_template("success.html", message="You are not logged in.")

    newreview = request.form.get("newreview")
    newstars = request.form.get("newstars")
    book = db.execute("SELECT * FROM books WHERE id = :book_id", {"book_id": book_id}).fetchone()
    reviews = db.execute("SELECT reviews.id, reviews.stars, reviews.review, reviews.user_id, reviews.book_id, users.name FROM reviews \
            JOIN users ON reviews.user_id=users.id WHERE book_id = :book_id", {"book_id": book_id})
    try:
        res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": "5EgIdTu1AvXOLH3FqL1xA", "isbns": book.ibsn}).json()
        gr_rating = res['books'][0]['average_rating']
        gr_rating_round = round(float(gr_rating))
        gr_reviews = res['books'][0]['work_ratings_count']
        gr_reviews = "{:,}".format(gr_reviews)
    except:
        gr_rating = "No data available"
        gr_reviews = "No data available"
        gr_rating_round = 0

    if (db.execute("SELECT * FROM reviews WHERE book_id = :book_id", {"book_id": book_id}).rowcount == 0):
        message = "No reviews yet! Be the first to add one!"
    else:
        message = ""

    if (db.execute("SELECT * FROM reviews WHERE (user_id = :curuser) AND (book_id = :book_id)",
            {"curuser": current_user, "book_id": book_id}).rowcount != 0):
        return render_template("book.html", book=book, reviews=reviews, gr_rating=gr_rating, gr_rating_round=gr_rating_round,
                gr_reviews=gr_reviews, message=message)
    elif (newreview == None or newstars == None):
        return render_template("bookreview.html", book=book, reviews=reviews, gr_rating=gr_rating, gr_rating_round=gr_rating_round,
                gr_reviews=gr_reviews, message=message)
    else:
        db.execute("INSERT INTO reviews (stars, review, user_id, book_id) VALUES (:newstars, :newreview, :curuser, :book_id)",
                {"newstars": newstars, "newreview": newreview, "curuser": current_user, "book_id": book_id})
        db.commit()
        reviews = db.execute("SELECT reviews.id, reviews.stars, reviews.review, reviews.user_id, reviews.book_id, users.name FROM reviews \
                JOIN users ON reviews.user_id=users.id WHERE book_id = :book_id", {"book_id": book_id})
        return render_template("book.html", book=book, reviews=reviews, gr_rating=gr_rating, gr_rating_round=gr_rating_round,
                gr_reviews=gr_reviews, message="")

@app.route("/api/<string:api_ibsn>")
def api(api_ibsn):
    if (db.execute("SELECT * FROM books WHERE ibsn = :ibsn", {"ibsn": api_ibsn}).rowcount == 0):
        return jsonify({"error": "That ibsn doesn't exist in the database"}), 404
    else:
        book = db.execute("SELECT * FROM books WHERE ibsn = :api_ibsn", {"api_ibsn": api_ibsn}).fetchone()
        reviews = db.execute("SELECT * FROM reviews WHERE book_id = :book_id", {"book_id": book.id}).rowcount
        if reviews == 0:
            avg_score = "Not Available"
        else:
            avg_score = float(db.execute("SELECT AVG(stars) FROM reviews WHERE book_id = :book_id", {"book_id": book.id}).fetchone().avg)
        return jsonify({
                "title": book.title,
                "author": book.author,
                "year": book.year,
                "ibsn": book.ibsn,
                "review_count": reviews,
                "average_score": avg_score
            })
