"""Emergency fix: add missing User columns to the production database.

This script is a safety net for cases where alembic migrations failed to run
on Render. It adds the columns needed by commit f18b86a (progressive
profiling) using raw SQL.

Usage (in Render shell or via a one-time manual run):
    python -c "import scripts.fix_missing_user_columns; scripts.fix_missing_user_columns.run()"
"""
import os
import sys

from sqlalchemy import text


COLUMNS_TO_ADD = [
    ("first_name", "VARCHAR(50)"),
    ("middle_name", "VARCHAR(50)"),
    ("last_name", "VARCHAR(50)"),
    ("must_complete_profile", "BOOLEAN NOT NULL DEFAULT FALSE"),
]


def run():
    """Add missing columns to the user table if they don't exist."""
    from payroll_engine import db, create_app

    app = create_app()
    with app.app_context():
        # Check current schema
        inspector = db.inspect(db.engine)
        existing_columns = {c["name"] for c in inspector.get_columns("user")}

        added = []
        skipped = []
        for col_name, col_type in COLUMNS_TO_ADD:
            if col_name in existing_columns:
                skipped.append(col_name)
                continue
            # SQLAlchemy 2.0 uses generic SQL with bind params
            sql = f'ALTER TABLE "user" ADD COLUMN {col_name} {col_type}'
            print(f'Adding column: {sql}')
            try:
                db.session.execute(text(sql))
                db.session.commit()
                added.append(col_name)
            except Exception as e:
                db.session.rollback()
                print(f'  Failed to add {col_name}: {e}')

        print(f'\nDone. Added: {added}. Skipped (already present): {skipped}')

        # Verify
        inspector = db.inspect(db.engine)
        final_columns = {c["name"] for c in inspector.get_columns("user")}
        for col_name, _ in COLUMNS_TO_ADD:
            status = "OK" if col_name in final_columns else "MISSING"
            print(f'  {col_name}: {status}')


if __name__ == "__main__":
    run()
