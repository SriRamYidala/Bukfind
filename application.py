import os
import requests
import json
from helpers import *

from flask import Flask, session,render_template,request,redirect,url_for,Markup,flash
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
    message=Markup("""<blockquote class="blockquote p-5 mt-5">
    <p>“A reader lives a thousand lives before he dies, said Jojen. <br>The man who never reads lives only one.”</p>
    <footer class="blockquote-footer">George R.R. Martin, A Dance with Dragons </footer>
    </blockquote>""")
    return render_template("index.html",message=message)


@app.route("/register", methods = ["GET", "POST"])
def register():
    session.clear()
    if request.method == "POST":
        if not request.form.get("email"):
            return render_template("error.html", message = "must provide username")

        username = request.form.get("email")

        userCheck = db.execute("SELECT * FROM users WHERE username = :username",
                                {"username": username}).fetchone()

        if userCheck:
            return render_template("error.html", message = "username already exist")

        elif not request.form.get("password"):
            return render_template("error.html", message = "must provide password")

        elif not request.form.get("confirmation"):
            return render_template("error.html", message = "must confirm password")

        elif not request.form.get("password") == request.form.get("confirmation"):
            return render_template("error.html", message = "passwords didnt match")

        password = request.form.get("password")

        db.execute("INSERT INTO users (username, password) VALUES (:username, :password)",
                    {"username": username, "password": password})

        db.commit()
        flash("Account created")

        return redirect("/login")

    else:
        return render_template("register.html")




@app.route("/login",methods=["GET","POST"])
def login():
    session.clear()
    #login_message = ""
    if request.method == "POST":
        username = request.form.get("email")
        password = request.form.get("password")

        data = db.execute("SELECT * FROM users WHERE username = :username",
                        {"username": username}).fetchone()
        if data != None:
            if data.username == username and data.password == password:
                session["username"] = username
                return redirect(url_for("search"))
            else:
                return render_template("login.html",log_in_message = "Wrong email or password. Try again.")

        else:
            render_template("login.html", log_in_message = "Wrong email or password. Try again.")

    return render_template("login.html")

@app.route("/search", methods = ["GET", "POST"])
@login_required
def search():
    username = session.get("username")
    message=Markup("""<blockquote class="blockquote p-5 mt-5">
    <p>“A reader lives a thousand lives before he dies, said Jojen. <br>The man who never reads lives only one.”</p>
    <footer class="blockquote-footer">George R.R. Martin, A Dance with Dragons </footer>
    </blockquote>""")
    session['books'] = []
    if request.method == "POST":
        message =''
        text = request.form.get("text")
        data = db.execute("SELECT * FROM books WHERE author iLIKE '%"+text+"%' OR title iLIKE '%"+text+"%' OR isbn iLIKE '%"+text+"%'").fetchall()
        for x in data:
            session['books'].append(x)
        if len(session['books'])==0:
            message = "Nothing found. Try again."
    
    return render_template("results.html", data = session['books'], message = message, username = username)

@app.route("/isbn/<string:isbn>", methods = ["GET", "POST"])
@login_required
def book(isbn):
    warning = ""
    username = session.get("username")
    session["reviews"] = []
    reviewtwice = db.execute("SELECT * FROM reviews WHERE isbn = :isbn AND username = :username",
                            {"isbn": isbn, "username": username}).fetchone()
    if request.method == "POST" and reviewtwice == None:
        review = request.form.get("textarea")
        rating = request.form.get("stars")
        db.execute("INSERT INTO reviews (isbn, review, rating, username) VALUES (:isbn, :review, :rating, :username)", 
                    {"isbn": isbn, "review": review, "rating": rating, "username": username})
        db.commit()

    if request.method == "POST" and reviewtwice != None:
        warning = "Sorry. You cannot add second review."

    res = requests.get("https://www.goodreads.com/book/review_counts.json", params = {"key": "VhPREPeJhqK8M3l9TBLQOQ", "isbns": isbn})
    average_rating = res.json()['books'][0]['average_rating']
    work_ratings_count = res.json()['books'][0]['work_ratings_count']
    reviews = db.execute("SELECT * FROM reviews WHERE isbn = :isbn", {"isbn": isbn}).fetchall()
    for y in reviews:
        session["reviews"].append(y)
    data = db.execute("SELECT * FROM books WHERE isbn = :isbn", {"isbn": isbn}).fetchone()
    return render_template("book.html", data = data, reviews = session['reviews'], average_rating = average_rating, work_ratings_count = work_ratings_count, username = username, warning = warning)


@app.route("/api/<string:isbn>")
@login_required
def api(isbn):
    data = db.execute("SELECT * FROM books WHERE isbn = :isbn", {"isbn": isbn}).fetchone()
    if data == None:
        return render_template("404.html")
    res = requests.get("https://www.goodreads.com/book/review_counts.json", params = {"key": "VhPREPeJhqK8M3l9TBLQOQ", "isbns": isbn})
    average_rating = res.json()['books'][0]['average_rating']
    work_ratings_count = res.json()['books'][0]['work_ratings_count']
    x = {
    "title": data.title,
    "author": data.author,
    "year": data.year,
    "isbn": isbn,
    "review_count": work_ratings_count,
    "average_score": average_rating
    }
    api = json.dumps(x)
    return render_template("api.json", api = api)
    
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))
