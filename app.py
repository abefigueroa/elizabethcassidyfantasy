from flask import Flask, render_template

app = Flask(__name__)


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/books")
def books():
    return render_template("books.html")


@app.route("/connect")
def connect():
    return render_template("connect.html")


@app.route("/draft-quest")
def draft_quest():
    return render_template("draft-quest/index.html")


if __name__ == "__main__":
    app.run(debug=True)