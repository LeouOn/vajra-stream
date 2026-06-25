#!/usr/bin/env python3
"""
Set up Vajra.Stream database.

This script is now a thin wrapper around :func:`core.schema.init_db` so
there is exactly ONE source of truth for the schema. Previously this
file had its own CREATE TABLE statements that drifted out of sync with
``core/schema.py`` — the columns/tables here diverged (e.g.
``healing_history`` had 16 columns here vs 5 in core/schema.py). The
legacy DDL has been removed; if you are maintaining the schema, edit
core/schema.py and it will be picked up by every code path.
"""

import argparse
import os
import sys


def create_database(db_path: str = "vajra_stream.db", *, force: bool = False):
    """
    Bootstrap the Vajra.Stream database by delegating to core.schema.init_db().

    Preserves the legacy user-facing behaviour:
      1. If the DB file exists, prompt before overwriting (skipped if force=True
         or stdin is not a TTY, so CI / piped contexts don't EOF)
      2. Print confirmation messages on success
    """
    # Prompt before clobbering an existing DB — matches the legacy UX.
    # Skip the prompt when --yes is passed OR stdin isn't interactive, so
    # this script works in CI and in piped contexts.
    if os.path.exists(db_path):
        if force or not sys.stdin.isatty():
            print(f"Database {db_path} already exists - overwriting (non-interactive).")
            os.remove(db_path)
        else:
            print(f"Database {db_path} already exists.")
            response = input("Overwrite? (y/n): ")
            if response.lower() != "y":
                print("Keeping existing database.")
                return
            os.remove(db_path)

    # Delegate to the single source of truth. core/schema.py is what every
    # production code path uses; setup_database.py is just the CLI bootstrap.
    # Add the project root to sys.path so `core.schema` resolves when this
    # script is run from the repo root via the README's documented command.
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)

    from core.schema import init_db, list_tables, get_db_path

    conn = init_db()
    try:
        tables = list_tables(conn)
    finally:
        conn.close()

    print("Creating tables...")
    print(f"\n[OK] Database initialized: {db_path or get_db_path()}")
    print(f"[OK] {len(tables)} tables created: {', '.join(tables)}")
    print("[OK] Schema is now sourced from core/schema.py (single source of truth)")
    print("\nDatabase ready for use!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Bootstrap the Vajra.Stream database.")
    parser.add_argument("--db", default="vajra_stream.db", help="Path to the SQLite database file")
    parser.add_argument("--yes", "-y", action="store_true", help="Overwrite existing DB without prompting")
    args = parser.parse_args()
    create_database(args.db, force=args.yes)

