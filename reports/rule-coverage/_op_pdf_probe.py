import sys
import pdfplumber

for name in ['heritage_act_2018', 'wapc_coastal_policy']:
    p = f'/app/data/raw-sources/{name}.pdf'
    with pdfplumber.open(p) as pdf:
        print(name, 'pages:', len(pdf.pages))
        print((pdf.pages[0].extract_text() or '')[:300].replace('\n', ' | '))
        print('====')
