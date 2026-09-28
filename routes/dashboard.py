from flask import Blueprint, redirect, render_template, request, session, url_for

from models import User, WordEntry, WritingGoal, db


dashboard_bp = Blueprint(
    "dashboard",
    __name__,
    url_prefix="/draft-quest",
)


@dashboard_bp.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))

    user = db.session.get(User, session["user_id"])

    if user is None:
        session.clear()
        return redirect(url_for("login"))

    error = None

    if request.method == "POST":
        target_words_input = request.form["target_words"].strip()

        try:
            target_words = int(target_words_input)
        except ValueError:
            error = "Your writing goal must be a whole number."
        else:
            if target_words <= 0:
                error = "Your writing goal must be greater than zero."
            else:
                if user.writing_goal is None:
                    goal = WritingGoal(
                        user_id=user.id,
                        target_words=target_words,
                    )

                    db.session.add(goal)

                else:
                    user.writing_goal.target_words = target_words

                db.session.commit()

                return redirect(url_for("dashboard.dashboard"))

    entries = db.session.execute(
        db.select(WordEntry)
        .where(WordEntry.user_id == user.id)
        .order_by(WordEntry.created_at.desc())
    ).scalars().all()

    total_words = sum(
        entry.words_written for entry in entries
    )

    if user.writing_goal:
        progress_percent = (
            total_words / user.writing_goal.target_words
        ) * 100

        progress_bar_percent = min(progress_percent, 100)
    else:
        progress_percent = 0
        progress_bar_percent = 0

    celebrate_goal = session.pop("celebrate_goal", False)

    return render_template(
        "draft-quest/dashboard.html",
        user=user,
        error=error,
        entries=entries,
        total_words=total_words,
        progress_percent=progress_percent,
        progress_bar_percent=progress_bar_percent,
        celebrate_goal=celebrate_goal,
    )


@dashboard_bp.route("/log-words", methods=["POST"])
def log_words():
    if "user_id" not in session:
        return redirect(url_for("login"))

    user = db.session.get(User, session["user_id"])

    if user is None:
        session.clear()
        return redirect(url_for("login"))

    words_input = request.form["words_written"].strip()

    try:
        words_written = int(words_input)
    except ValueError:
        return redirect(url_for("dashboard.dashboard"))

    if words_written <= 0:
        return redirect(url_for("dashboard.dashboard"))

    previous_total = sum(
        entry.words_written for entry in user.word_entries
    )

    new_total = previous_total + words_written

    entry = WordEntry(
        user_id=user.id,
        words_written=words_written,
    )

    db.session.add(entry)
    db.session.commit()

    if (
        user.writing_goal
        and previous_total < user.writing_goal.target_words
        and new_total >= user.writing_goal.target_words
    ):
        session["celebrate_goal"] = True

    return redirect(url_for("dashboard.dashboard"))