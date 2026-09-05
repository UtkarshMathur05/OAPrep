"""Apply database/init/*.sql and (later) backfill problem embeddings.

Usage:  python -m app.db.init_db [--embed]

Not required for normal startup — docker compose runs the same SQL on the first
boot of an empty volume. Use this to re-apply after editing the schema.
"""


def main() -> None:
    raise NotImplementedError


if __name__ == "__main__":
    main()
