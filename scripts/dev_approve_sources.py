"""Dev-only: auto-approve all pending source versions on startup."""
from draftcheck.db.session import get_engine
from sqlalchemy import text

engine = get_engine()
with engine.connect() as conn:
    n = conn.execute(
        text("UPDATE source_versions SET review_status='approved' WHERE review_status='pending_review'")
    ).rowcount
    conn.commit()
    print(f"dev auto-approved {n} source versions")
