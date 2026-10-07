import sqlite3
from datetime import datetime, timezone
from pathlib import Path


def migrate():
    database_path = Path(__file__).parent / "instance" / "draft_quest.db"

    if not database_path.is_file():
        raise RuntimeError("Database not found.")

    with sqlite3.connect(database_path) as connection:
        columns = {
            row[1]
            for row in connection.execute("PRAGMA table_info(user)")
        }

        if not columns:
            raise RuntimeError("User table not found.")

        if "profile_image" in columns:
            print("Profile image column already exists.")
            return

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
        backup_path = database_path.with_name(
            f"draft_quest-before-profile-image-{timestamp}.db"
        )

        with sqlite3.connect(backup_path) as backup:
            connection.backup(backup)

        connection.execute(
            "ALTER TABLE user ADD COLUMN profile_image VARCHAR(255)"
        )

    print("Backup created and profile image column added.")


if __name__ == "__main__":
    migrate()