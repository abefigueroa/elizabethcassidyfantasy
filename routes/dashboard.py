from datetime import datetime, timedelta, timezone

from flask import (
    Blueprint,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from models import User, WordEntry, WritingGoal, db


dashboard_bp = Blueprint(
    "dashboard",
    __name__,
    url_prefix="/draft-quest",
)


def current_user():
    """Look up the user identified by the login session."""
    user_id = session.get("user_id")

    if user_id is None:
        return None

    user = db.session.get(User, user_id)

    if user is None:
        session.clear()

    return user


def read_goal_form():
    """Validate the project name and target submitted by a form."""
    project_name = request.form.get("project_name", "").strip()

    if not project_name:
        return None, None, "Enter the name of the work you are writing."

    if len(project_name) > 200:
        return None, None, "The project name must be 200 characters or fewer."

    try:
        target_words = int(request.form.get("target_words", "").strip())
    except ValueError:
        return None, None, "Your writing goal must be a whole number."

    if target_words <= 0:
        return None, None, "Your writing goal must be greater than zero."

    return project_name, target_words, None


@dashboard_bp.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    user = current_user()

    if user is None:
        return redirect(url_for("login"))

    error = None
    goal = user.writing_goal

    if request.method == "POST":
        project_name, target_words, error = read_goal_form()

        if error is None:
            if goal is None:
                goal = WritingGoal(
                    user_id=user.id,
                    project_name=project_name,
                    target_words=target_words,
                )
                db.session.add(goal)
            else:
                goal.project_name = project_name
                goal.target_words = target_words

            db.session.commit()
            return redirect(url_for("dashboard.dashboard"))

    entries = []

    if goal is not None:
        entries = db.session.execute(
            db.select(WordEntry)
            .where(
                WordEntry.user_id == user.id,
                WordEntry.goal_id == goal.id,
            )
            .order_by(
                WordEntry.created_at.desc(),
                WordEntry.id.desc(),
            )
        ).scalars().all()

    total_words = sum(entry.words_written for entry in entries)

    today = datetime.now(timezone.utc).date()
    week_start = today - timedelta(days=today.weekday())

    weekly_totals = {
        week_start + timedelta(days=offset): 0
        for offset in range(7)
    }

    for entry in entries:
        entry_date = entry.created_at.date()

        if entry_date in weekly_totals:
            weekly_totals[entry_date] += entry.words_written

    writing_dates = {
        entry.created_at.date()
        for entry in entries
    }

    writing_streak = 0
    streak_day = today

    if streak_day not in writing_dates:
        streak_day -= timedelta(days=1)

    while streak_day in writing_dates:
        writing_streak += 1
        streak_day -= timedelta(days=1)

    progress_percent = (
        total_words / goal.target_words * 100
        if goal is not None
        else 0
    )

    return render_template(
        "draft-quest/dashboard.html",
        user=user,
        error=error,
        entries=entries,
        total_words=total_words,
        today=today.isoformat(),
        weekly_totals=weekly_totals,
        writing_streak=writing_streak,
        progress_percent=progress_percent,
        progress_bar_percent=min(progress_percent, 100),
        celebrate_goal=session.pop("celebrate_goal", False),
    )


@dashboard_bp.route("/log-words", methods=["POST"])
def log_words():
    user = current_user()

    if user is None:
        return redirect(url_for("login"))

    goal = user.writing_goal

    if goal is None:
        flash("Set a writing goal before logging words.", "error")
        return redirect(url_for("dashboard.dashboard"))

    try:
        words_written = int(
            request.form.get("words_written", "").strip()
        )
    except ValueError:
        words_written = 0

    if words_written <= 0:
        flash("Words written must be a whole number greater than zero.", "error")
        return redirect(url_for("dashboard.dashboard"))

    date_input = request.form.get("entry_date", "").strip()

    try:
        entry_date = datetime.strptime(date_input, "%Y-%m-%d").date()
    except ValueError:
        flash("Choose a valid writing date.", "error")
        return redirect(url_for("dashboard.dashboard"))

    if entry_date > datetime.now(timezone.utc).date():
        flash("Writing dates cannot be in the future.", "error")
        return redirect(url_for("dashboard.dashboard"))

    previous_total = db.session.execute(
        db.select(
            db.func.coalesce(db.func.sum(WordEntry.words_written), 0)
        ).where(
            WordEntry.user_id == user.id,
            WordEntry.goal_id == goal.id,
        )
    ).scalar_one()

    entry = WordEntry(
        user_id=user.id,
        goal_id=goal.id,
        words_written=words_written,
        created_at=datetime.combine(
            entry_date,
            datetime.min.time(),
            tzinfo=timezone.utc,
        ),
    )

    db.session.add(entry)
    db.session.commit()

    if previous_total < goal.target_words <= previous_total + words_written:
        session["celebrate_goal"] = True

    return redirect(url_for("dashboard.dashboard"))


@dashboard_bp.route("/new-goal", methods=["POST"])
def new_goal():
    user = current_user()

    if user is None:
        return redirect(url_for("login"))

    project_name, target_words, error = read_goal_form()

    if error:
        flash(error, "error")
        return redirect(url_for("dashboard.dashboard"))

    previous_goal = user.writing_goal

    if previous_goal is not None:
        previous_goal.is_active = False
        previous_goal.ended_at = datetime.now(timezone.utc)

        # Release the active-goal slot before inserting the new goal.
        # Both changes still belong to the same transaction.
        db.session.flush()

    db.session.add(
        WritingGoal(
            user_id=user.id,
            project_name=project_name,
            target_words=target_words,
        )
    )

    db.session.commit()
    session.pop("celebrate_goal", None)

    flash("Your new quest is ready. Previous entries remain in history.", "success")
    return redirect(url_for("dashboard.dashboard"))


@dashboard_bp.route("/history")
def history():
    user = current_user()

    if user is None:
        return redirect(url_for("login"))

    entries = db.session.execute(
        db.select(WordEntry)
        .options(db.joinedload(WordEntry.goal))
        .where(WordEntry.user_id == user.id)
        .order_by(
            WordEntry.created_at.desc(),
            WordEntry.id.desc(),
        )
    ).scalars().all()

    return render_template(
        "draft-quest/history.html",
        user=user,
        entries=entries,
        lifetime_words=sum(entry.words_written for entry in entries),
    )


@dashboard_bp.route("/history/clear", methods=["POST"])
def clear_history():
    user = current_user()

    if user is None:
        return redirect(url_for("login"))

    if request.form.get("confirm_clear") != "yes":
        flash("Confirm deletion before clearing your history.", "error")
        return redirect(url_for("dashboard.history"))

    db.session.execute(
        db.delete(WordEntry).where(WordEntry.user_id == user.id)
    )

    db.session.commit()
    session.pop("celebrate_goal", None)

    flash("Your writing history has been cleared.", "success")

    return redirect(url_for("dashboard.history"))