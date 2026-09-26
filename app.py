from flask import Flask, render_template, redirect, request, url_for
from werkzeug.security import generate_password_hash

from models import User, db


app = Flask(__name__)

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///draft_quest.db"

db.init_app(app)


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


@app.route("/draft-quest/register", methods=["GET", "POST"])
def register():
    error = None

    if request.method == "POST":
        email = request.form["email"].strip().lower()
        display_name = request.form["display_name"].strip()
        password = request.form["password"]

        existing_email = db.session.execute(
            db.select(User).where(User.email == email)
        ).scalar_one_or_none()

        existing_display_name = db.session.execute(
            db.select(User).where(User.display_name == display_name)
        ).scalar_one_or_none()

        if not email or not display_name or not password:
            error = "All fields are required."
        elif existing_email:
            error = "An account with that email already exists."
        elif existing_display_name:
            error = "That display name is already taken."
        else:
            user = User(
                email=email,
                display_name=display_name,
                password_hash=generate_password_hash(password),
            )

            db.session.add(user)
            db.session.commit()

            return redirect(url_for("draft_quest"))

    return render_template(
        "draft-quest/register.html",
        error=error,
    )


def main() -> None:
    with app.app_context():
        db.create_all()

    app.run(debug=True)


if __name__ == "__main__":
    main()