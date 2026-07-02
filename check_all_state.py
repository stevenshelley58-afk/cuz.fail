import sys
sys.path.insert(0, "/usr/local/lib/python3.12/site-packages")
from draftcheck.db.engine import create_runtime_engine
from sqlalchemy import text

engine = create_runtime_engine()

with engine.begin() as conn:
    result = conn.execute(text("""
        SELECT status, COUNT(*) FROM target_manifest GROUP BY status ORDER BY status;
    """))
    for row in result:
        print(f"  {row[0]}: {row[1]}")
    
    # Count source_versions
    result = conn.execute(text("SELECT COUNT(*) FROM source_versions;"))
    print(f"\n  source_versions: {result.scalar()}")
    
    # Count rules
    result = conn.execute(text("SELECT lifecycle_status, COUNT(*) FROM rules GROUP BY lifecycle_status ORDER BY lifecycle_status;"))
    print(f"\n  rules:")
    for row in result:
        print(f"    {row[0]}: {row[1]}")
    
    # Count clauses
    result = conn.execute(text("SELECT disposition, COUNT(*) FROM clauses GROUP BY disposition ORDER BY disposition;"))
    print(f"\n  clauses:")
    for row in result:
        print(f"    {row[0]}: {row[1]}")
    
    # Count legal_edges
    result = conn.execute(text("SELECT COUNT(*) FROM legal_edges;"))
    print(f"\n  legal_edges: {result.scalar()}")
    
    result = conn.execute(text("SELECT COUNT(*) FROM legal_edges WHERE review_status = 'pending_review';"))
    print(f"  pending_review edges: {result.scalar()}")
    
    result = conn.execute(text("SELECT COUNT(*) FROM legal_edges WHERE evidence_quote IS NULL OR evidence_quote = '';"))
    print(f"  quoteless edges: {result.scalar()}")
    
    # Rule-bearing without rules
    result = conn.execute(text("""
        SELECT COUNT(*) FROM clauses c 
        WHERE disposition = 'rule_bearing' 
        AND NOT EXISTS (SELECT 1 FROM rules r WHERE r.clause_id = c.id);
    """))
    print(f"\n  rule-bearing clauses without rules: {result.scalar()}")
    
    # Adversarial findings
    result = conn.execute(text("SELECT COUNT(*) FROM adversarial_findings;"))
    print(f"\n  adversarial_findings: {result.scalar()}")
    
    # Eval cases
    result = conn.execute(text("SELECT COUNT(*) FROM eval_cases;"))
    print(f"  eval_cases: {result.scalar()}")
