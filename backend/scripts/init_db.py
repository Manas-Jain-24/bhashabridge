"""Apply schema migrations and seed the learning catalog."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main():
    from app.models.database import init_db

    try:
        init_db()
    except Exception as exc:
        print(f"Database setup failed ({type(exc).__name__}). Check configuration and schema.", file=sys.stderr)
        return 1
    print("Database schema and learning catalog are current.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
