import sys
import re
import pdfplumber

path, pattern, out = sys.argv[1], sys.argv[2], sys.argv[3]
rx = re.compile(pattern, re.IGNORECASE)
hits = []
with pdfplumber.open(path) as pdf:
    for i, page in enumerate(pdf.pages):
        text = page.extract_text() or ''
        lines = text.split('\n')
        for j, line in enumerate(lines):
            if rx.search(line):
                ctx = ' || '.join(lines[max(0, j-1):j+2])
                hits.append(f'[p{i+1}] {ctx}')
        if len(hits) > 60:
            break
with open(out, 'w', encoding='utf-8') as f:
    f.write('\n'.join(hits[:60]))
print(f'{len(hits)} hits -> {out}')
