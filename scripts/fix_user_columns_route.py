"""One-time migration fix route. Add this temporarily to __init__.py to run
on Render, then remove once columns are added.

To use:
1. Add to payroll_engine/__init__.py:
   from scripts.fix_user_columns_route import register_fix_route
   register_fix_route(app)
2. Push to Render
3. Visit /admin/fix-user-columns (one-time)
4. Remove the import + registration
5. Push again to clean up
"""
from flask import jsonify

from payroll_engine import db


def register_fix_route(app):
    """Register a one-time endpoint to add missing User columns."""

    @app.route("/admin/fix-user-columns", methods=["GET", "POST"])
    def fix_user_columns():
        from sqlalchemy import text
        from sqlalchemy.exc import OperationalError

        COLUMNS = [
            ("first_name", "VARCHAR(50)"),
            ("middle_name", "VARCHAR(50)"),
            ("last_name", "VARCHAR(50)"),
            ("must_complete_profile", "BOOLEAN NOT NULL DEFAULT FALSE"),
        ]

        try:
            inspector = db.inspect(db.engine)
            existing = {c["name"] for c in inspector.get_columns("user")}

            results = {"added": [], "skipped": [], "errors": []}
            for col_name, col_type in COLUMNS:
                if col_name in existing:
                    results["skipped"].append(col_name)
                    continue
                # Use dialect-appropriate ALTER TABLE
                dialect = db.engine.dialect.name
                if dialect == "postgresql":
                    sql = f'ALTER TABLE "user" ADD COLUMN {col_name} {col_type}'
                elif dialect == "sqlite":
                    # SQLite doesn't support NOT NULL DEFAULT in ADD COLUMN for some versions
                    nullable = "" if "NOT NULL" in col_type else "NULL"
                    default = " DEFAULT FALSE" if "must_complete_profile" in col_name else ""
                    sql = f'ALTER TABLE "user" ADD COLUMN {col_name} {col_type.replace("NOT NULL DEFAULT FALSE", "NULL" + default)}'
                elif dialect == "mysql":
                    sql = f'ALTER TABLE `user` ADD COLUMN {col_name} {col_type}'
                else:
                    sql = f'ALTER TABLE "user" ADD COLUMN {col_name} {col_type}'

                try:
                    db.session.execute(text(sql))
                    db.session.commit()
                    results["added"].append(col_name)
                except OperationalError as e:
                    db.session.rollback()
                    results["errors"].append({"column": col_name, "error": str(e)})

            # Verify
            inspector = db.inspect(db.engine)
            final = {c["name"] for c in inspector.get_columns("user")}
            for col_name, _ in COLUMNS:
                results.setdefault("status", {})[col_name] = (
                    "OK" if col_name in final else "MISSING"
                )
            return jsonify({"ok": True, "results": results})
        except Exception as e:
            db.session.rollback()
            return jsonify({"ok": False, "error": str(e)}), 500
