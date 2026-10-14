import json, re
sil = {}
for l in open('work/sil.txt'):
    c, rest = l.split(' ', 1)
    v = [float(x) for x in re.findall(r': ([0-9.]+)', rest)]
    sil[c] = list(zip(v[0::2], v[1::2]))
KEEP = [  # (clip, in, out, label)
    ('c1', 0.45, 16.70, 'hook'),
    ('c2', 0.00, 5.14, 'intro'),
    ('c2', 6.58, 11.86, 'rm10k'),
    ('c2', 28.95, 40.13, 'planner'),
    ('c2', 44.04, 55.36, 'next'),
    ('c3', 0.00, 20.50, 'breakdown'),
    ('c3', 62.90, 75.10, 'baby'),
    ('c3', 81.40, 94.48, 'easier'),
    ('c3', 94.48, 97.30, 'honestA'),
    ('c3', 101.06, 117.28, 'honestB'),
    ('c3', 117.75, 133.05, 'progress'),
]
edl = []
for clip, a, b, lab in KEEP:
    cuts = [(s, e) for s, e in sil[clip] if e - s >= 0.5 and s > a + 0.1 and e < b - 0.1]
    pieces, cur = [], a
    for s, e in cuts:
        pieces.append((cur, s + 0.08)); cur = e - 0.08
    pieces.append((cur, b))
    for k, (i, o) in enumerate(pieces):
        if o - i < 0.3: continue
        edl.append({'id': f'{lab}{k}' if len(pieces) > 1 else lab, 'clip': clip, 'in': round(i, 3), 'out': round(o, 3)})
# alternate framing between consecutive same-clip segments to hide jump cuts
z = False
for k, s in enumerate(edl):
    if k and edl[k - 1]['clip'] == s['clip']: z = not z
    else: z = False
    s.update({'zoom': 1.18 if z else 1.0, 'cx': 0.5, 'cy': 0.5})
json.dump(edl, open('edl.json', 'w'), indent=1)
tot = sum(s['out'] - s['in'] for s in edl)
for s in edl: print(s['id'], s['clip'], s['in'], s['out'], s['zoom'])
print(len(edl), 'segments', round(tot, 1), 's')
