import re

import sqlglot
from sqlglot import exp


class UnsafeQueryError(Exception):
    """Raised when generated SQL is unsafe or invalid."""
    pass


# ============================================================
# BLOCKED SQL OPERATIONS
# ============================================================

BLOCKED_KEYWORDS = {
    "DROP",
    "DELETE",
    "UPDATE",
    "INSERT",
    "ALTER",
    "ATTACH",
    "PRAGMA",
    "CREATE",
    "REPLACE",
    "VACUUM",
    "REINDEX",
    "TRUNCATE",
}


# ============================================================
# SQL VALIDATOR
# ============================================================

def validate_sql(sql: str) -> str:
    """
    Validate Gemini-generated SQL.

    Requirements:
    - Must contain exactly one SQL statement
    - Must be a SELECT query
    - Blocks destructive/database-modifying operations
    - Uses SQLGlot parsing to verify syntax
    """

    if not sql or not sql.strip():
        raise UnsafeQueryError("Empty SQL query.")

    sql = sql.strip()

    # --------------------------------------------------------
    # Remove markdown fences if Gemini accidentally adds them
    # --------------------------------------------------------

    sql = (
        sql
        .replace("```sql", "")
        .replace("```sqlite", "")
        .replace("```", "")
        .strip()
    )

    # --------------------------------------------------------
    # Remove one harmless trailing semicolon
    # --------------------------------------------------------

    sql = sql.rstrip(";").strip()

    if not sql:
        raise UnsafeQueryError("Empty SQL query.")

    # --------------------------------------------------------
    # BLOCK MULTIPLE STATEMENTS
    # --------------------------------------------------------

    if ";" in sql:
        raise UnsafeQueryError(
            "Multiple SQL statements are not allowed."
        )

    # --------------------------------------------------------
    # BLOCK DANGEROUS KEYWORDS
    # --------------------------------------------------------

    upper_sql = sql.upper()

    for keyword in BLOCKED_KEYWORDS:

        # Match keyword as a complete SQL word.
        pattern = rf"\b{re.escape(keyword)}\b"

        if re.search(pattern, upper_sql):
            raise UnsafeQueryError(
                f"Unsafe SQL operation blocked: {keyword}"
            )

    # --------------------------------------------------------
    # PARSE SQL WITH SQLGLOT
    # --------------------------------------------------------

    try:
        parsed = sqlglot.parse_one(
            sql,
            read="sqlite"
        )

    except Exception as e:
        raise UnsafeQueryError(
            f"Invalid SQL syntax: {str(e)}"
        )

    # --------------------------------------------------------
    # ONLY SELECT QUERIES ARE ALLOWED
    # --------------------------------------------------------

    if not isinstance(parsed, exp.Select):
        raise UnsafeQueryError(
            "Only SELECT queries are allowed."
        )

    # --------------------------------------------------------
    # RETURN CLEAN SQL
    # --------------------------------------------------------

    return parsed.sql(dialect="sqlite")