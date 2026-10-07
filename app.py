import os
import string

from dotenv import load_dotenv
from flask import Flask, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from models import User, WordEntry, WritingGoal, db
from routes.dashboard import dashboard_bp
from email_validator import EmailNotValidError, validate_email


load_dotenv()

app = Flask(__name__)

app.config["SECRET_KEY"] = os.environ["SECRET_KEY"]
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///draft_quest.db"

db.init_app(app)
app.register_blueprint(dashboard_bp)

def normalize_email(value):
    try:
        result = validate_email(
            value.strip(),
            check_deliverability=False, 
        )
    except EmailNotValidError:
        return None

    if len(result.normalized) > 255:
        return None

    return result.normalized.lower()

def is_valid_password(password):
    return (
        len(password) >= 8
        and any(character.isupper() for character in password)
        and any(character in string.digits for character in password)
        and any(character in string.punctuation for character in password)
    )

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

# Profile
@app.route("/draft-quest/profile", methods=["GET", "POST"])
def profile():
    user_id = session.get("user_id")
    user = db.session.get(User, user_id) if user_id is not None else None

    if user is None:
        session.clear()
        return redirect(url_for("login"))

    error = None

    if request.method == "POST":
        display_name = request.form.get("display_name", "").strip()
        email = normalize_email(request.form.get("email", ""))

        if not display_name or len(display_name) > 50:
            error = "Username must be between 1 and 50 characters."
        elif email is None:
            error = "Please enter a valid email address."
        else:
            existing_name = db.session.execute(
                db.select(User).where(
                    User.display_name == display_name,
                    User.id != user.id,
                )
            ).scalar_one_or_none()

            existing_email = db.session.execute(
                db.select(User).where(
                    User.email == email,
                    User.id != user.id,
                )
            ).scalar_one_or_none()

            if existing_name:
                error = "That username is already taken."
            elif existing_email:
                error = "An account with that email already exists."
            else:
                user.display_name = display_name
                user.email = email
                db.session.commit()
                return redirect(url_for("profile"))

    return render_template(
        "draft-quest/profile.html",
        user=user,
        error=error,
    )

@app.route("/draft-quest/change-password", methods=["POST"])
def change_password():
    user_id = session.get("user_id")
    user = db.session.get(User, user_id) if user_id is not None else None

    if user is None:
        session.clear()
        return redirect(url_for("login"))

    current_password = request.form.get("current_password", "")
    new_password = request.form.get("new_password", "")
    confirm_password = request.form.get("confirm_password", "")

    password_error = None

    if not check_password_hash(user.password_hash, current_password):
        password_error = "Your current password is incorrect."
    elif not is_valid_password(new_password):
        password_error = (
            "New password must contain at least 8 characters, "
            "an uppercase letter, a number, and a special character."
        )
    elif new_password != confirm_password:
        password_error = "The new passwords do not match."
    elif new_password == current_password:
        password_error = "Choose a password different from your current one."

    if password_error:
        return render_template(
            "draft-quest/profile.html",
            user=user,
            password_error=password_error,
        )

    user.password_hash = generate_password_hash(new_password)
    db.session.commit()

    session.clear()
    session["user_id"] = user.id

    return redirect(url_for("profile"))

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