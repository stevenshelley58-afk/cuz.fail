import pdfplumber

with pdfplumber.open('/app/data/raw-sources/heritage_act_2018.pdf') as pdf:
    for pno in (61, 62, 66):
        t = pdf.pages[pno-1].extract_text() or ''
        print(f'--- page {pno} ---')
        print(t[:1800])
