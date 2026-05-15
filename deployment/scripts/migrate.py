from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy import create_engine, text


def discover_migrations(migrations_dir: Path) -> list[Path]:
    return sorted(path for path in migrations_dir.glob("*.sql") if path.is_file())


def normalize_database_url(database_url: str) -> str:
    if database_url.startswith("postgresql://"):
        return "postgresql+psycopg://" + database_url.removeprefix("postgresql://")
    return database_url


def main() -> None:
    database_url = normalize_database_url(os.getenv("DATABASE_URL", "sqlite+pysqlite:///:memory:"))
    engine = create_engine(database_url, future=True)
    migrations = discover_migrations(Path("progrec_service/db/migrations"))
    with engine.begin() as connection:
        connection.exec_driver_sql(
            "CREATE TABLE IF NOT EXISTS schema_migrations (version TEXT PRIMARY KEY, applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"
        )
        applied = {row[0] for row in connection.execute(text("SELECT version FROM schema_migrations"))}
        for path in migrations:
            if path.name in applied:
                continue
            sql = path.read_text(encoding="utf-8")
            for statement in [chunk.strip() for chunk in sql.split(";") if chunk.strip()]:
                connection.exec_driver_sql(statement)
            connection.execute(
                text("INSERT INTO schema_migrations (version) VALUES (:version)"),
                {"version": path.name},
            )
            print(f"applied {path.name}")


if __name__ == "__main__":
    main()
