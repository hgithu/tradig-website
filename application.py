#api key pk_09b0b2300b8441719eaf22646526f8b2
import os

from cs50 import SQL
from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    stocks = db.execute("SELECT stock, shares FROM stocks WHERE id=:id ORDER BY stock DESC", id=session["user_id"])
    symb = db.execute("SELECT stock FROM stocks WHERE id=:id ORDER BY stock DESC", id=session["user_id"])
    print(stocks)
    i = 0;
    value = 0;
    for stock in symb:
        for x in stock.values():
            stocks[i].update({'price' : lookup(x)['price']})
            stocks[i].update({'value' : (lookup(x)['price'] * stocks[i]['shares'])})
            value = value + stocks[i]['value']
            i += 1
    cash = db.execute("SELECT cash FROM users WHERE id=:id", id=session["user_id"])
    value = cash[0]['cash'] + value
    return render_template("index.html", stocks=stocks, cash=cash[0]['cash'], value=value)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method == "POST":
        symbol = lookup(request.form.get("symbol"))
        if symbol is None:
            return apology("bad symbol")
        shares = request.form.get("shares")
        cash = int((db.execute("SELECT cash FROM users WHERE id = :id", id=session["user_id"]))[0]["cash"])
        if (int(shares) * int(symbol["price"])) > cash:
            return apology("not enough money$$$$$$$$$")
        if not list(db.execute("SELECT stock FROM stocks WHERE (id=:id AND stock=:symbol)", id=session["user_id"], symbol=symbol["symbol"])):
            db.execute("INSERT INTO stocks (id, stock, shares) VALUES (:id, :stock, :share);", id=session["user_id"], stock=symbol["symbol"], share=shares)
        else:
            s = int((db.execute("SELECT shares FROM stocks WHERE id=:id AND stock=:symbol", id=session["user_id"], symbol=symbol["symbol"]))[0]["shares"])
            db.execute("UPDATE stocks SET shares= :shares WHERE id=:id AND stock=:symbol", shares=s + int(shares), id=session["user_id"], symbol=symbol["symbol"])
        db.execute("INSERT INTO trades (id, buy_sell, stock, shares) VALUES (:id, :buy, :stock, :shares)", id=session["user_id"], buy="buy", stock=symbol["symbol"], shares=shares)
        db.execute("UPDATE users SET cash = :cost WHERE id=:id", cost=cash-float(symbol["price"])*int(shares), id=session["user_id"])
        return redirect("/")

    else:
        return render_template("buy.html")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    history= db.execute("SELECT stock, shares, time, buy_sell FROM trades WHERE id=:id", id=session["user_id"])
    return render_template("history.html", history=history)


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
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

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


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    if request.method == "GET":
        return render_template("quote.html")

    if request.method == "POST":
        stock_quote = lookup(request.form.get("symbol"))
        if stock_quote is None:
            return apology("stock quote cannot be accesed")
        return render_template("quoted.html", stock=stock_quote)


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "POST":

        #check if post is filled
        if not request.form.get("username"):
            return apology("must provide username", 403)
        elif not request.form.get("password"):
            return apology("must provide password", 403)
        elif not request.form.get("confirmation"):
            return apology("must provide password conformation", 403)

        #check if username exists or passwords are correct
        username = request.form.get("username")
        if db.execute("SELECT username FROM users WHERE username = :name", name=username):
            return apology("username is taken", 400)
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")
        if password != confirmation:
            return apology("password and conformation password are different", 400)

        #place data in database
        db.execute("INSERT INTO users (username, hash) VALUES(:user, :hashpass)", user=username, hashpass=generate_password_hash(password))
        return redirect("/")
    else:
        return render_template("register.html")



@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    if request.method == "POST":
        symbol = (request.form.get("symbol").upper())
        if symbol is None:
            return apology("bad symbol")
        shares = request.form.get("shares")
        if int(shares) < 0:
            return apology("please enter a positive number")
        if not list(db.execute("SELECT stock FROM stocks WHERE id=:id AND stock=:symbol", id=session["user_id"], symbol=symbol.upper())):
            return apology("user doesnt have this stock")
        current_shares = int(db.execute("SELECT shares FROM stocks WHERE id=:id AND stock=:symbol", id=session["user_id"], symbol=symbol.upper())[0]['shares'])
        if current_shares < int(shares):
            return apology("you do not have enough shares")
        current_cash = db.execute("SELECT cash FROM users WHERE id=:id", id=session["user_id"])
        price = (int(shares)*float(lookup(symbol)['price']))
        db.execute("UPDATE users SET cash=:cash WHERE id=:id", cash = float(current_cash[0]['cash'] + price), id=session["user_id"])
        if current_shares == int(shares):
            db.execute("DELETE FROM stocks WHERE id=:id AND stock=:symbol", id=session["user_id"], symbol=symbol)
        db.execute("UPDATE stocks SET shares=:s WHERE id=:id AND stock=:symbol", s=current_shares - int(shares), id=session["user_id"], symbol=symbol)
        db.execute("INSERT INTO trades (id, buy_sell, stock, shares) VALUES (:id, :buy, :stock, :shares)", id=session["user_id"], buy="sell", stock=symbol, shares=shares)
        return redirect("/")
    else:
        return render_template("sell.html")


def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
