"""SELECT-only access enforced in SQLite, beyond the rubric's prefix validator."""
import re
import sqlite3
from contextlib import closing

TABLES = frozenset({"sales", "customers", "employees"})
FUNCTIONS = frozenset({"sum", "avg", "count", "min", "max", "round", "coalesce",
                       "nullif", "strftime", "date", "julianday", "abs", "lower", "upper",
                       "length", "substr", "like", "trim", "total", "ifnull", "cast"})


def clean_sql_output(raw_sql):
    """Strip surrounding Markdown; preserve SQL string literals and identifiers."""
    return re.sub(r"^```(?:sql)?\s*|\s*```$", "", raw_sql.strip(), flags=re.I).strip()


def validate_sql(query):
    # The SQLite authorizer is the security boundary; this check provides a clear
    # early error and intentionally rejects CTEs to match the SELECT-only rubric.
    if not re.match(r"^SELECT\b", query.strip(), re.I):
        return {"valid": False, "reason": "Only SELECT queries are permitted"}
    return {"valid": True, "reason": "Prefix checked; SQLite authorization still required"}


def connect_readonly(path):
    if not path.is_file():
        raise FileNotFoundError("Database missing. Run python setup_db.py first.")
    return sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True, timeout=2)


def schema_context(path):
    with closing(connect_readonly(path)) as conn:
        schemas = [row[0] for row in conn.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name IN ('sales','customers','employees')")]
        if len(schemas) != len(TABLES):
            raise ValueError("Database must contain sales, customers and employees tables.")
        return "\n".join(schemas)


def execute_select(sql, settings):
    check = validate_sql(sql)
    if not check["valid"]:
        raise ValueError(check["reason"])

    def authorize(action, first, second, database, trigger):
        if action == sqlite3.SQLITE_SELECT:
            return sqlite3.SQLITE_OK
        # SQLite reports no database/column for its optimised COUNT(*) table scan.
        # ATTACH is denied, and the table allowlist still applies in that case.
        if action == sqlite3.SQLITE_READ and database in ("main", None) and first in TABLES:
            return sqlite3.SQLITE_OK
        if action == sqlite3.SQLITE_FUNCTION and (second or "").lower() in FUNCTIONS:
            return sqlite3.SQLITE_OK
        return sqlite3.SQLITE_DENY

    with closing(connect_readonly(settings.database)) as conn:
        conn.execute("PRAGMA query_only = ON")
        conn.set_authorizer(authorize)
        steps = 0

        def stop_expensive_query():
            nonlocal steps
            steps += 1000
            return int(steps > settings.sql_steps)

        conn.set_progress_handler(stop_expensive_query, 1000)
        # execute, unlike executescript, rejects multiple statements.
        cursor = conn.execute(sql)
        rows = cursor.fetchmany(settings.max_rows + 1)
        return {"columns": [d[0] for d in cursor.description],
                "rows": rows[:settings.max_rows], "truncated": len(rows) > settings.max_rows}
