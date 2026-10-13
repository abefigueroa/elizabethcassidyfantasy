import secrets
import resend

from flask import (
    Blueprint, render_template, request, session,
    redirect, url_for, current_app
)
from datetime import datetime, timezone, timedelta
from resend.exceptions import ResendError
from werkzeug.security import (
    generate_password_hash,
    check_password_hash,
)

from models import db, User, PasswordReset
from validators import normalize_email, is_valid_password


password_reset_bp = Blueprint(
    "password_reset",
    __name__,
    url_prefix="/draft-quest",
)


@password_reset_bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    error = None
    message = None

    if request.method == "POST":
        email = normalize_email(request.form.get("email", ""))

        if email is None:
            error = "Please enter a valid email address."
        else:
            session["password_reset_email"] = email
            user = db.session.execute(
                db.select(User).where(User.email == email)
            ).scalar_one_or_none()
            message = (
                "If an account exists for that email address, "
                "we'll send a password reset code."
            )

            if user is not None:
                latest_reset = db.session.execute(
                    db.select(PasswordReset)
                    .where(PasswordReset.user_id == user.id)
                    .order_by(PasswordReset.created_at.desc())
                    .limit(1)
                ).scalar_one_or_none()

                if latest_reset is not None:
                    last_requested_at = latest_reset.created_at.replace(tzinfo=timezone.utc)
                    elapsed = datetime.now(timezone.utc) - last_requested_at
                    if elapsed < timedelta(seconds=60):
                        return redirect(url_for("password_reset.verify_reset_code"))
                    
                unused_resets = db.session.execute(
                    db.select(PasswordReset).where(
                        PasswordReset.user_id == user.id,
                        PasswordReset.used_at.is_(None),
                    )
                ).scalars().all()

                for old_reset in unused_resets:
                    old_reset.used_at = datetime.now(timezone.utc)
                    
                sender = "Draft Quest <noreply@mail.elizabethcassidyfantasy.com>"
                code_number = secrets.randbelow(1_000_000)
                code = f"{code_number:06d}"
                code_hash = generate_password_hash(code)
                email_body = (
                    f"Your Draft Quest password reset code is: {code}\n\n"
                    "This code expires in 10 minutes. "
                    "Enter it on the Draft Quest website to continue resetting your password.\n\n"
                    "If you didn't request a password reset, you can ignore this email. "
                    "Your password was not changed."
                )
                email_params = {
                    "from": sender,
                    "to": [user.email],
                    "subject": "Your Draft Quest password reset code",
                    "text": email_body,
                }
                expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)
                reset_request = PasswordReset(
                    user_id=user.id,
                    code_hash=code_hash,
                    expires_at=expires_at,
                )

                db.session.add(reset_request)
                db.session.commit()
                try:
                    resend.Emails.send(email_params)
                except ResendError:
                    current_app.logger.error("Password reset email delivery failed.")

            return redirect(url_for("password_reset.verify_reset_code"))
                    
    return render_template(
        "draft-quest/forgot-password.html",
        error=error,
        message=message,
    )     


@password_reset_bp.route("/verify-reset-code", methods=["GET", "POST"])
def verify_reset_code():
    email = session.get("password_reset_email")

    if email is None:
        return redirect(url_for("password_reset.forgot_password"))

    error = None

    if request.method == "POST":
        code = request.form.get("code", "").strip()

        if len(code) != 6 or any(
            character not in "0123456789"
            for character in code
        ):
            error = "Please enter a six-digit reset code."
    
    return render_template(
        "draft-quest/verify-reset-code.html",
        error=error,
    )
