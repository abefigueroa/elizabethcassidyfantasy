from uuid import uuid4

from flask import (
    Blueprint, current_app, redirect, render_template,
    request, session, url_for,
)
from PIL import Image, ImageOps, UnidentifiedImageError
from werkzeug.security import check_password_hash, generate_password_hash

from models import User, db
from validators import is_valid_password, normalize_email


profile_bp = Blueprint(
    "profile",
    __name__,
    url_prefix="/draft-quest",
)

def save_profile_image(upload):
    try:
        with Image.open(upload.stream) as image:
            if image.format not in {"JPEG", "PNG", "WEBP"}:
                raise ValueError("Choose a JPEG, PNG, or WebP image.")

            if image.width * image.height > 10_000_000:
                raise ValueError("Choose an image under 10 megapixels.")

            image.load()
            image = ImageOps.exif_transpose(image)
            avatar = ImageOps.fit(
                image.convert("RGBA"),
                (400, 400),
                method=Image.Resampling.LANCZOS,
            )
    except (
        UnidentifiedImageError,
        OSError,
        Image.DecompressionBombError,
    ) as exc:
        raise ValueError("That file could not be read as an image.") from exc

    folder = current_app.config["PROFILE_IMAGE_FOLDER"]
    folder.mkdir(parents=True, exist_ok=True)

    filename = f"{uuid4().hex}.png"
    avatar.save(folder / filename, format="PNG")

    return filename

@profile_bp.route("/profile", methods=["GET", "POST"])
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
                upload = request.files.get("profile_image")

                if upload is not None and upload.filename:
                    try:
                        user.profile_image = save_profile_image(upload)
                    except ValueError as exc:
                        error = str(exc)
                if error is None:
                    user.display_name = display_name
                    user.email = email
                    db.session.commit()        
                    return redirect(url_for("profile.profile"))

    return render_template(
        "draft-quest/profile.html",
        user=user,
        error=error,
    )

@profile_bp.route("/profile-image", methods=["POST"])
def profile_image():
    user_id = session.get("user_id")
    user = db.session.get(User, user_id) if user_id is not None else None

    if user is None:
        session.clear()
        return redirect(url_for("login"))

    upload = request.files.get("profile_image")

    if upload is None or upload.filename == "":
        return redirect(url_for("profile.profile"))
    elif upload is not None and upload.filename:
        previous_image = user.profile_image

        try:
            user.profile_image = save_profile_image(upload)
        except ValueError as exc:
            error = str(exc)

            return render_template(
                "draft-quest/profile.html",
                user=user,
                error=error,
            )

        db.session.commit()

        if previous_image:
            previous_path = (
                current_app.config["PROFILE_IMAGE_FOLDER"] / previous_image
            )
            try:
                previous_path.unlink(missing_ok=True)
            except OSError:
                current_app.logger.warning(
                    "Could not delete the previous profile image.",
                    exc_info=True,
                )
        return redirect(url_for("profile.profile"))

@profile_bp.route("/change-password", methods=["POST"])
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

    return redirect(url_for("profile.profile"))
