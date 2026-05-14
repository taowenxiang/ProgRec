from __future__ import annotations

from pathlib import Path


def discover_migrations(migrations_dir: Path) -> list[Path]:
    return sorted(path for path in migrations_dir.glob("*.sql") if path.is_file())


def main() -> None:
    for path in discover_migrations(Path("progrec_service/db/migrations")):
        print(path.name)


if __name__ == "__main__":
    main()
