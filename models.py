from datetime import datetime, timezone

from flask_sqlalchemy import SQLAlchemy


db = SQLAlchemy()


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    display_name = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    profile_image = db.Column(db.String(255), nullable=True)

    writing_goals = db.relationship(
        "WritingGoal",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    word_entries = db.relationship(
        "WordEntry",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    @property
    def writing_goal(self):
        """Return the user's active writing goal."""
        return next(
            (
                goal
                for goal in self.writing_goals
                if goal.is_active
            ),
            None,
        )

    def __repr__(self):
        return f"<User {self.display_name}>"


class WritingGoal(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=False,
    )

    project_name = db.Column(
        db.String(200),
        nullable=False,
    )

    target_words = db.Column(
        db.Integer,
        nullable=False,
    )

    is_active = db.Column(
        db.Boolean,
        default=True,
        nullable=False,
    )

    created_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    ended_at = db.Column(
        db.DateTime,
        nullable=True,
    )

    user = db.relationship(
        "User",
        back_populates="writing_goals",
    )

    entries = db.relationship(
        "WordEntry",
        back_populates="goal",
    )

    # SQLite allows multiple archived goals, but only one active
    # goal per user.
    __table_args__ = (
        db.Index(
            "uq_writing_goal_active_user",
            "user_id",
            unique=True,
            sqlite_where=db.text("is_active = 1"),
        ),
    )

    def __repr__(self):
        return f"<WritingGoal {self.project_name}: {self.target_words}>"


class WordEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=False,
    )

    goal_id = db.Column(
        db.Integer,
        db.ForeignKey("writing_goal.id"),
        nullable=True,
    )

    words_written = db.Column(
        db.Integer,
        nullable=False,
    )

    created_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    user = db.relationship(
        "User",
        back_populates="word_entries",
    )

    goal = db.relationship(
        "WritingGoal",
        back_populates="entries",
    )

    def __repr__(self):
        return f"<WordEntry {self.words_written}>"