import json
d = json.load(open('reports/verification_results.json'))
print('summary keys:', list(d['summary'].keys()))
print('summary:', d['summary'])
