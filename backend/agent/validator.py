"""
Validates model-generated SQL before it touches the database.

The original version of this project used a keyword substring check
(`"drop" in sql.lower()`). That approach has two real failure modes:
  1. It can't tell "SELECT * FROM merchant_orders" (safe) from a string that
     happens to contain "update" inside a quoted value (false positive).
  2. It can't stop "SELECT 1; DROP TABLE reconciliation_results;" — statement
     chaining sails straight through a substring check (false negative, and
     the dangerous one).

This version parses the SQL into an AST with sqlglot and checks the *shape*
of the query, not just the words in it.
"""
import sqlglot
from sqlglot import exp

ALLOWED_TABLES = {
    "reconciliation_results",
    "merchant_orders",
    "gateway_ledgers",
    "bank_statements",
}


class UnsafeQueryError(Exception):
    pass


def validate_sql(sql: str) -> str:
    """Raises UnsafeQueryError if the SQL isn't a single, read-only, in-schema
    SELECT statement. Returns the (single) validated statement's SQL on success."""

    try:
        statements = sqlglot.parse(sql, read="sqlite")
    except Exception as e:
        raise UnsafeQueryError(f"Could not parse SQL: {e}")

    statements = [s for s in statements if s is not None]

    if len(statements) != 1:
        raise UnsafeQueryError(
            f"Expected exactly one statement, got {len(statements)} — statement chaining is blocked."
        )

    stmt = statements[0]

    if not isinstance(stmt, exp.Select):
        raise UnsafeQueryError(f"Only SELECT statements are allowed, got {type(stmt).__name__}.")

    # Block any DML/DDL node that could theoretically ride inside a subquery
    # or CTE (e.g. sqlite's INSERT ... RETURNING tricks, PRAGMA calls).
    forbidden_node_types = (exp.Insert, exp.Update, exp.Delete, exp.Drop,
                             exp.Alter, exp.Attach, exp.Pragma, exp.Create)
    forbidden_hits = list(stmt.find_all(*forbidden_node_types))
    if forbidden_hits:
        raise UnsafeQueryError(f"Disallowed operation: {type(forbidden_hits[0]).__name__}")

    referenced_tables = {t.name.lower() for t in stmt.find_all(exp.Table)}
    unknown_tables = referenced_tables - ALLOWED_TABLES
    if unknown_tables:
        raise UnsafeQueryError(f"Query references unknown table(s): {unknown_tables}")

    return stmt.sql(dialect="sqlite")
