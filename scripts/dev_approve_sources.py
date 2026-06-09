"""Dev-only: auto-approve all pending source versions on startup."""
from draftcheck.db.engine import create_runtime_engine
from sqlalchemy import text

engine = create_runtime_engine()
with engine.connect() as conn:
    n = conn.execute(text(
        "UPDATE source_versions SET review_status='approved', licence_status='open'"
        " WHERE review_status='pending_review' OR licence_status='pending_review'"
    )).rowcount
    conn.commit()
    print(f"dev auto-approved {n} source versions")
