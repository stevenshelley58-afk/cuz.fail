import os
import re
import json
import psycopg
import pdfplumber

url = os.environ['DATABASE_URL'].replace('postgresql+asyncpg://', 'postgresql://').replace('postgresql+psycopg://', 'postgresql://')
storage = os.getenv('DRAFTCHECK_STORAGE_ROOT', '/srv/draftcheck/storage')

with psycopg.connect(url) as c:
    cur = c.cursor()
    cur.execute("""SELECT conname FROM pg_constraint WHERE conrelid='clauses'::regclass AND contype='u'""")
    print('clause unique constraints:', cur.fetchall())
    cur.execute("""SELECT v.id, v.storage_manifest_json FROM source_versions v
                   WHERE v.id IN ('f8e39d86-40bb-479c-80c4-ccfd9f76234d','a925e8ae-951c-43bf-aa29-c14d26b3c67d','483aca28-d2c7-4f42-99f8-080bf7fed8ec')""")
    rows = cur.fetchall()

for vid, manifest in rows:
    m = manifest if isinstance(manifest, dict) else json.loads(manifest)
    sp = m.get('storage_path')
    path = os.path.join(storage, sp) if sp and not sp.startswith('/') else sp
    print('---', vid, path, os.path.exists(path) if path else None)
    if not path or not os.path.exists(path):
        continue
    try:
        with pdfplumber.open(path) as pdf:
            print('pages:', len(pdf.pages))
            targets = {
                'f8e39d86-40bb-479c-80c4-ccfd9f76234d': r'duty to report|known or suspected|report a contaminated|11\.',
                'a925e8ae-951c-43bf-aa29-c14d26b3c67d': r'adjoining owner|dividing fence|notice|contribute',
                '483aca28-d2c7-4f42-99f8-080bf7fed8ec': r'water service works|connect|sewer',
            }[vid]
            rx = re.compile(targets, re.IGNORECASE)
            hits = 0
            for i, page in enumerate(pdf.pages[:80]):
                text = page.extract_text() or ''
                lines = text.split('\n')
                for j, line in enumerate(lines):
                    if rx.search(line) and hits < 12:
                        print(f'[p{i+1}] ' + ' || '.join(lines[max(0, j-1):j+2])[:400])
                        hits += 1
    except Exception as e:
        print('ERR', e)
