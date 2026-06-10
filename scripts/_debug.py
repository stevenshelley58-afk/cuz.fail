"""Debug helper: figure out why the db is empty after run."""
import os
os.chdir(r"C:\Dev\Cuz\.claude\worktrees\objective-rubin-7d1432")
print("DATABASE_URL:", os.getenv("DATABASE_URL"))
print("APP_ENV:", os.getenv("APP_ENV"))
print("CWD:", os.getcwd())
print("db exists:", os.path.exists("draftcheck-corpus.db"), os.path.getsize("draftcheck-corpus.db") if os.path.exists("draftcheck-corpus.db") else 0)

# Try opening directly with same URL the script would use
import sqlite3
c = sqlite3.connect("sqlite:///./draftcheck-corpus.db", engine={"uri": True})
print("opened:", c)
