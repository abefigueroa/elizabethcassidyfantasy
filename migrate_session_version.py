import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from contextlib import closing


def migrate():
    database_path = Path(__file__).parent / "instance" / "draft_quest.db"

    if not database_path.is_file():
        raise RuntimeError("Database not found.")

    with closing(sqlite3.connect(database_path)) as connection, connection:
        column_rows = connection.execute(
            "PRAGMA table_info(user)"
        ).fetchall()

        columns = {row[1] for row in column_rows}

        if not columns:
            raise RuntimeError("User table not found.")
        
        if "session_version" in columns:
            print("Session version column already exists.")
            return

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
        backup_path = database_path.with_name(
            f"draft_quest-before-session-version-{timestamp}.db"
        )

        with closing(sqlite3.connect(backup_path)) as backup:
            connection.backup(backup)

        connection.execute(
            "ALTER TABLE user ADD COLUMN session_version INTEGER NOT NULL DEFAULT 0"
        )


if __name__ == "__main__":
    migrate()

        

