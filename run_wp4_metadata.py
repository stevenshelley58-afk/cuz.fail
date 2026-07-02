import sys
sys.path.insert(0, "/usr/local/lib/python3.12/site-packages")
from draftcheck.db.engine import create_runtime_engine
from sqlalchemy import text

engine = create_runtime_engine()

with engine.begin() as conn:
    # Check canonical_url values for pending rows
    result = conn.execute(text("""
        SELECT canonical_url IS NULL as is_null, COUNT(*)
        FROM target_manifest
        WHERE status = 'pending'
        GROUP BY 1;
    """))
    for row in result:
        print(f"  is_null={row[0]}: count={row[1]}")

    # Mark NULL URL pending rows as metadata_only
    result = conn.execute(text("""
        UPDATE target_manifest
        SET status = 'metadata_only',
            notes = 'No resolvable URL; cited but unfetchable'
        WHERE status = 'pending'
          AND canonical_url IS NULL
        RETURNING id;
    """))
    rows = result.fetchall()
    print(f"Marked {len(rows)} NULL-URL rows as metadata_only")

    # Check remaining
    result = conn.execute(text("""
        SELECT status, COUNT(*) FROM target_manifest GROUP BY status ORDER BY status;
    """))
    for row in result:
        print(f"  {row[0]}: {row[1]}")
