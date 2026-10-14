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
    ('c2', 44.04, 55.45, 'next'),
    ('c3', 0.00, 20.50, 'breakdown'),
    ('c3', 62.90, 75.10, 'baby'),
    ('c3', 81.40, 94.48, 'easier'),
    ('c3', 94.48, 97.30, 'honestA'),
    ('c3', 101.06, 117.28, 'honestB'),
    ('c3', 117.75, 133.05, 'progress'),
]
sil50 = {}
for l in open('work/sil50.txt'):
    c, rest = l.split(' ', 1)
    v = [float(x) for x in re.findall(r': ([0-9.]+)', rest)]
    sil50[c] = list(zip(v[0::2], v[1::2]))


def tail(clip, t):
    """where the voice has really died away after t (-50 dB), so soft word endings ("progress", "goal") survive"""
    nxt = [a for a, b in sil50[clip] if a >= t - .05]
    return min(nxt) if nxt else t + .3


def onset(clip, t):
    """next speech after t (end of the next -35 dB silence)"""
    nxt = [e for s_, e in sil[clip] if s_ >= t - .05]
    return min(nxt) if nxt else 1e9


edl = []
for n, (clip, a, b, lab) in enumerate(KEEP):
    cuts = [(s_, e) for s_, e in sil[clip] if e - s_ >= 0.5 and s_ > a + 0.1 and e < b - 0.1]
    pieces, cur = [], a
    for s_, e in cuts:
        # never end before the word has decayed; never start later than 0.12s before the next word
        pieces.append((cur, max(s_ + .12, min(tail(clip, s_) + .08, e - .14)))); cur = e - 0.12
    last = n == len(KEEP) - 1
    cap = b + (.6 if last else .25)
    nxt = KEEP[n + 1] if not last else None
    if nxt and nxt[0] == clip and nxt[1] >= b - .01:
        cap = min(cap, nxt[1] - .02)      # the next section continues straight on in the same clip
    pieces.append((cur, min(tail(clip, b - .25) + (.45 if last else .10), onset(clip, b) - .08, cap)))
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
