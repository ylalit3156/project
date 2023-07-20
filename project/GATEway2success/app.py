import os
import calendar

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError

from helpers import apology, login_required

# Configure application
app = Flask(__name__)


# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///applicant.db")

@app.route('/')
@login_required
def home():
    user_id = session["user_id"]
    year = 2023  # Specify the year
    month = 7    # Specify the month

    cal = calendar.monthcalendar(year, month)

    date_colors = {}

    current_date = datetime.now().date()
    for week in cal:
        for day in week:
            if day != 0:
                date = datetime(year, month, day).date()

                # just monitor the current date
                if date < current_date:  # for past
                    checkout = db.execute("SELECT TIME(checkout) AS checkout FROM attendance WHERE user_id = ? AND DATE(checkout) = ?", (user_id), (date))
                    checkin = db.execute("SELECT TIME(check_in) AS checkin FROM attendance WHERE user_id = ? AND DATE(check_in) = ?", (user_id), (date))
                    if checkout and checkin:
                        time_checkout = datetime.strptime(checkout[0]["checkout"], "%H:%M:%S")
                        time_checkin = datetime.strptime(checkin[0]["checkin"], "%H:%M:%S")
                        time_diff = time_checkout - time_checkin
                        time_diff_sec = time_diff.total_seconds()
                        if time_diff_sec > 21600:
                            date_colors[date] = 'green'
                        else:
                            date_colors[date] = 'red'
                        print(time_diff_sec)
                    else:
                        date_colors[date] = 'red'

                elif date == current_date:  # for present
                    checkout = db.execute("SELECT TIME(checkout) AS checkout FROM attendance WHERE user_id = ? AND DATE(checkout) = ?", (user_id), (date))
                    checkin = db.execute("SELECT TIME(check_in) AS checkin FROM attendance WHERE user_id = ? AND DATE(check_in) = ?", (user_id), (date))
                    if checkout and checkin:
                        time_checkout = datetime.strptime(checkout[0]["checkout"], "%H:%M:%S")
                        time_checkin = datetime.strptime(checkin[0]["checkin"], "%H:%M:%S")
                        time_diff = time_checkout - time_checkin
                        time_diff_sec = time_diff.total_seconds()
                        if time_diff_sec > 21600:
                            date_colors[date] = 'green'
                        else:
                            date_colors[date] = 'red'
                        print(time_diff_sec)



    # return render_teemplate for each day
    return render_template('index.html', cal=cal, year=year, month=month, date_colors=date_colors, datetime=datetime)

@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    # If user reached route via GET, display registration form
    if request.method == "GET":
        return render_template("register.html")

    # If user reached route via POST, process registration
    else:
        # Get form data
        username = request.form.get("username")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")

        # Validate form data
        if not username:
            return apology("must provide username")
        elif not password:
            return apology("must provide password")
        elif not confirmation:
            return apology("must confirm password")
        elif password != confirmation:
            return apology("passwords must match")
        else:
            # Generate password hash
            hash = generate_password_hash(password)

            # Insert new user into database
            result = db.execute("INSERT INTO users (username, hash) VALUES (:username, :hash)",
                                 username=username, hash=hash)

            # Check if username is already taken
            if not result:
                return apology("username already taken")

            # Log user in and redirect to index page
            rows = db.execute("SELECT * FROM users WHERE username = :username", username=username)
            session["user_id"] = rows[0]["id"]
            flash("Registered!")
            return redirect("/")


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")



@app.route("/attendance", methods=["GET", "POST"])
@login_required
def attendance():
    # If user reached route via GET, display checkin form
    user_id = session["user_id"]
    if request.method == "GET":
        return render_template("attendance.html")
    else:
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        symbol = request.form.get("symbol")
        if symbol == "checkin":
            #Check if check-in exists for the user
            checkin_exists = db.execute("SELECT check_in FROM attendance WHERE user_id = ? AND DATE(check_in) = DATE(?)", (user_id), (now))
            if checkin_exists:
                return apology("Check-in already recorded")
            else:
                db.execute("INSERT INTO attendance (check_in, user_id) VALUES (?, ?)", (now), (session["user_id"]))
                # Redirect the user to the index page
                flash("checked in")
                return redirect("/")

        elif symbol == "checkout":
            #Check if check-in exists for the user
            checkin_exists = db.execute("SELECT check_in FROM attendance WHERE user_id = ? AND DATE(check_in) = DATE(?)", (user_id), (now))
            if not checkin_exists:
                return apology("Not checked-in")
            checkout_exists = db.execute("SELECT checkout FROM attendance WHERE user_id = ? AND DATE(checkout) = DATE(?)", (user_id), (now))
            if checkout_exists:
                return apology("Checkout already exists")
            db.execute("UPDATE attendance SET checkout = ? WHERE user_id = ? AND DATE(check_in) = DATE(?) ", (now), (user_id), (now))
            # Redirect the user to the index page
            flash("checked out")
            return redirect("/")

        else:
            return apology("Nothing found")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/notes", methods=["GET", "POST"])
@login_required
def notes():
    """ write some text topic that you studied and then no. of qs you solved and submit"""
    user_id = session["user_id"]
    if request.method == "POST":
        topic = request.form.get("topic")
        if not topic:
            flash("You need to give the topic")
            return render_template("notes.html")
        questions = request.form.get("questions")
        if not questions:
            flash("no. of Qs mandatory")
            return render_template("notes.html")
        now = datetime.now()

        # add to the database
        result = db.execute("INSERT INTO memory (user_id, date, topic, questions) VALUES (?,?,?,?)", (user_id), (now), (topic), (questions))
        flash("note recorded")
        return render_template("notes.html")
    return render_template("notes.html")


@app.route("/progress")
@login_required
def progress():
    """Show history of transactions"""
    user_id = session["user_id"]
    if not user_id:
        return apology("Not logged in")

    progress = db.execute("SELECT date, topic, questions FROM memory WHERE user_id = ?",(user_id,))
    return render_template("progress.html", progress = progress)

