import os

from dotenv import load_dotenv
from flask import Flask, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash
from pathlib import Path

from models import User, WordEntry, WritingGoal, db
from routes.dashboard import dashboard_bp
from validators import is_valid_password, normalize_email
from routes.profile import profile_bp


load_dotenv()

app = Flask(__name__)

app.config["SECRET_KEY"] = os.environ["SECRET_KEY"]
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///draft_quest.db"
app.config["PROFILE_IMAGE_FOLDER"] = (
    Path(app.root_path) / "static" / "uploads" / "profiles"
)
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024  # 5 MB

db.init_app(app)
app.register_blueprint(dashboard_bp)
app.register_blueprint(profile_bp)

@app.route("/")
def home():
    return render_template("index.html")


@app.route("/books")
def books():
    return render_template("books.html")


@app.route("/draft-quest")
def draft_quest():
    user_id = session.get("user_id")
    user = db.session.get(User, user_id) if user_id is not None else None

    if user is not None:
        return redirect(url_for("dashboard.dashboard"))

    session.pop("user_id", None)

    return render_template("draft-quest/index.html")

# Login
@app.route("/draft-quest/login", methods=["GET", "POST"])
def login():
    error = None

    if request.method == "POST":
        email = request.form["email"].strip().lower()
        password = request.form["password"]

        if not email or not password:
            error = "Email and password are required."
        else:
            user = db.session.execute(
                db.select(User).where(User.email == email)
            ).scalar_one_or_none()

            if user is None or not check_password_hash(
                user.password_hash,
                password,
            ):
                error = "Invalid email or password."
            else:
                session.clear()
                session["user_id"] = user.id

                return redirect(url_for("dashboard.dashboard"))

    return render_template(
        "draft-quest/login.html",
        error=error,
    )

# Registration
@app.route("/draft-quest/register", methods=["GET", "POST"])
def register():
    error = None

    if request.method == "POST":
        email = normalize_email(request.form["email"])
        display_name = request.form["display_name"].strip()
        password = request.form["password"]

        existing_email = db.session.execute(
            db.select(User).where(User.email == email)
        ).scalar_one_or_none()

        existing_display_name = db.session.execute(
            db.select(User).where(User.display_name == display_name)
        ).scalar_one_or_none()

        if not display_name or not password:
            error = "All fields are required."
        elif email is None:
            error = "Please enter a valid email address."
        elif not is_valid_password(password):
            error = (
                "Password must contain at least 8 characters, "
                "an uppercase letter, a number, and a special character."
            )
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

            session.clear()
            session["user_id"] = user.id

            return redirect(url_for("dashboard.dashboard"))

    return render_template(
        "draft-quest/register.html",
        error=error,
    )

# Logout
@app.route("/draft-quest/logout", methods=["POST"])
def logout():
    session.clear()

    return redirect(url_for("draft_quest"))


def main() -> None:
    with app.app_context():
        db.create_all()

    app.run(debug=True)


if __name__ == "__main__":
    main()
