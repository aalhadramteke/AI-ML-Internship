"""
Database Query Tool (Practical Project)
---------------------------------------
Safe, read-only SQL access to a SQLite database for an LLM agent.

Safety layers:
  1. Only a single SELECT / WITH statement is accepted
  2. Forbidden keywords (INSERT, DROP, ...) are rejected
  3. Database opened in read-only mode (mode=ro)
  4. Row limit so the LLM context is never flooded
"""
import csv
import os
import re
import sqlite3

FORBIDDEN = re.compile(
    r"\b(insert|update|delete|drop|alter|create|replace|attach|detach|pragma|vacuum|truncate)\b",
    re.IGNORECASE,
)


class DBQueryError(Exception):
    """Raised for any validation / query problem. Message is LLM-friendly."""


def validate_sql(sql: str) -> str:
    s = (sql or "").strip().rstrip(";").strip()
    if not s:
        raise DBQueryError("Empty query.")
    if ";" in s:
        raise DBQueryError("Only a single SQL statement is allowed.")
    if not re.match(r"^(select|with)\b", s, re.IGNORECASE):
        raise DBQueryError("Only SELECT queries are allowed.")
    if FORBIDDEN.search(s):
        raise DBQueryError("Query contains a forbidden keyword (read-only tool).")
    return s


def _connect_ro(db_path: str) -> sqlite3.Connection:
    if not os.path.exists(db_path):
        raise DBQueryError(f"Database not found: {db_path}")
    return sqlite3.connect(f"file:{os.path.abspath(db_path)}?mode=ro", uri=True)


def get_schema(db_path: str) -> dict:
    """Return {table: [{name, type}, ...]} so the LLM can write correct SQL."""
    conn = _connect_ro(db_path)
    try:
        tables = [r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
        return {
            t: [{"name": c[1], "type": c[2]} for c in conn.execute(f'PRAGMA table_info("{t}")')]
            for t in tables
        }
    finally:
        conn.close()


def run_query(db_path: str, sql: str, max_rows: int = 100) -> dict:
    s = validate_sql(sql)
    conn = _connect_ro(db_path)
    try:
        cur = conn.execute(s)
        rows = cur.fetchmany(max_rows + 1)
        cols = [d[0] for d in cur.description] if cur.description else []
        truncated = len(rows) > max_rows
        rows = [list(r) for r in rows[:max_rows]]
        return {"columns": cols, "rows": rows, "row_count": len(rows), "truncated": truncated}
    except sqlite3.Error as e:
        raise DBQueryError(f"SQL error: {e}. Check table/column names with action='schema'.")
    finally:
        conn.close()


def load_csv_to_db(csv_path: str, db_path: str, table: str) -> int:
    """Helper for setup/demo: load a CSV into a SQLite table (all columns TEXT/auto)."""
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", table):
        raise DBQueryError("Invalid table name.")
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader)
        rows = list(reader)
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(f'DROP TABLE IF EXISTS "{table}"')
        conn.execute(f'CREATE TABLE "{table}" ({", ".join(chr(34) + h + chr(34) for h in header)})')
        conn.executemany(f'INSERT INTO "{table}" VALUES ({",".join("?" * len(header))})', rows)
        conn.commit()
    finally:
        conn.close()
    return len(rows)
