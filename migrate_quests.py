import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from app import app
from models import db


def migrate():
    with app.app_context():
        database_path = Path(db.engine.url.database)

    if not database_path.is_file():
        raise RuntimeError(f"Database not found: {database_path}")

    connection = sqlite3.connect(database_path)

    try:
        goal_columns = {
            row[1]
            for row in connection.execute(
                "PRAGMA table_info(writing_goal)"
            )
        }

        entry_columns = {
            row[1]
            for row in connection.execute(
                "PRAGMA table_info(word_entry)"
            )
        }

        if "project_name" in goal_columns or "goal_id" in entry_columns:
            raise RuntimeError(
                "Database already changed. Do not run this migration again."
            )

        if goal_columns != {
            "id", "user_id", "target_words", "created_at"
        } or entry_columns != {
            "id", "user_id", "words_written", "created_at"
        }:
            raise RuntimeError("Database does not match the expected old schema.")

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
        backup_path = database_path.with_name(
            f"draft_quest-before-quests-{timestamp}.db"
        )

        with sqlite3.connect(backup_path) as backup:
            connection.backup(backup)

        print(f"Backup created: {backup_path}")

        connection.execute("PRAGMA foreign_keys = OFF")
        connection.execute("BEGIN IMMEDIATE")

        connection.execute("""
            CREATE TABLE writing_goal_new (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES user(id),
                project_name VARCHAR(200) NOT NULL,
                target_words INTEGER NOT NULL,
                is_active BOOLEAN NOT NULL,
                created_at DATETIME NOT NULL,
                ended_at DATETIME
            )
        """)

        connection.execute("""
            INSERT INTO writing_goal_new (
                id, user_id, project_name, target_words,
                is_active, created_at, ended_at
            )
            SELECT
                id, user_id, 'Untitled Project', target_words,
                1, created_at, NULL
            FROM writing_goal
        """)

        connection.execute("DROP TABLE writing_goal")
        connection.execute(
            "ALTER TABLE writing_goal_new RENAME TO writing_goal"
        )

        connection.execute("""
            CREATE UNIQUE INDEX uq_writing_goal_active_user
            ON writing_goal(user_id)
            WHERE is_active = 1
        """)

        connection.execute("""
            ALTER TABLE word_entry
            ADD COLUMN goal_id INTEGER REFERENCES writing_goal(id)
        """)

        connection.execute("""
            UPDATE word_entry
            SET goal_id = (
                SELECT writing_goal.id
                FROM writing_goal
                WHERE writing_goal.user_id = word_entry.user_id
            )
        """)

        problems = connection.execute(
            "PRAGMA foreign_key_check"
        ).fetchall()

        if problems:
            raise RuntimeError(f"Foreign key check failed: {problems}")

        connection.commit()
        print("Migration complete. Existing entries have been preserved.")

    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


if __name__ == "__main__":
    migrate()