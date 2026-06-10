import sqlite3
db = r"C:\Dev\Cuz\.claude\worktrees\objective-rubin-7d1432\draftcheck-corpus.db"
c = sqlite3.connect(db, timeout=10)
c.execute("PRAGMA foreign_keys = OFF")
cur = c.execute("select name from sqlite_master where type='table'")
tables = [r[0] for r in cur.fetchall()]
for t in tables:
    try:
        c.execute(f"drop table if exists {t}")
        print(f"dropped {t}")
    except Exception as e:
        print(f"FAIL {t}: {e}")
c.commit()
c.close()
print("done")
