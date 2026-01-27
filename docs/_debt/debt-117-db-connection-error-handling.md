# DEBT-117: Database Connection Error Handling Fragile

**Priority:** P2
**Status:** Open
**Found:** 2026-01-27
**Component:** `src/erdos/core/search/db.py`

## Summary

The `SearchDatabase.connect()` context manager has fragile error handling. If `sqlite3.connect()` raises, the finally block will try to close a connection that doesn't exist.

## Evidence

```python
# src/erdos/core/search/db.py:126-135
@contextmanager
def connect(self) -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(self._db_path)  # Could raise here
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()  # conn exists if we get here
        raise
    finally:
        conn.close()  # If line 126 raised, conn is undefined!
```

## Actual Behavior

If `sqlite3.connect()` raises (e.g., disk full, permission denied), the code reaches the `finally` block where `conn.close()` will raise `UnboundLocalError`.

## Expected Behavior

Connection errors should be handled cleanly without secondary exceptions.

## Recommended Fix

```python
@contextmanager
def connect(self) -> Iterator[sqlite3.Connection]:
    conn: sqlite3.Connection | None = None
    try:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        yield conn
        conn.commit()
    except Exception:
        if conn is not None:
            conn.rollback()
        raise
    finally:
        if conn is not None:
            conn.close()
```

## Impact

- Medium: Secondary exceptions obscure the real error
- Affects: Edge cases (disk full, permissions, corrupted DB)
- Current: Works in happy path; fragile on errors

## Related

- AUDIT-012: Database connection error handling
