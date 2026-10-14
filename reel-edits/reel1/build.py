#!/usr/bin/env python3
"""reel1: Malay goal-setting reel, cool girl look throughout (built from the /video-edit template machinery).

Captions: calm cream Inter lines, word by word, in the chest band; they hop to the top band while a motion graphic
owns the chest band. Punch words: yellow Instrument Serif italic, tucked behind the head (cutout on top).
Motion graphics (all inline GSAP): RM10k counter, planner page written by hand, "tengok je" struck through,
goal break-down tree, baby-step checklist, progress bar.

PY build.py           writes index.html
PY build.py --safe    same + red Instagram safe-zone guide (snapshots only)
"""
import json
import os
import shutil
import subprocess
import sys

SAFE = '--safe' in sys.argv or bool(os.environ.get('SAFE'))
LAYER = os.environ.get('LAYER', '')   # 'back' / 'front': graphics only, transparent, for the ffmpeg composite
DUR = float(subprocess.run([shutil.which('ffprobe') or 'ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries',
                            'stream=duration', '-of', 'csv=p=0', 'assets/aroll.mp4'],
                           capture_output=True, encoding='utf-8', errors='replace').stdout.strip().split(',')[0])
YEL = '#FAE67A'
CREAM = '#FFF8EF'
with open('segments.json', encoding='utf-8') as _f:
    SEGS = json.load(_f)
SEG = {s['id']: s for s in SEGS}
CUTS = [s['frame'] / 30 - .002 for s in SEGS[1:]]
# Every time below was measured on the v2 cut (times from 104.6s on were measured on v1 and go through S first).
# v3 lets each sentence finish (no clipped word endings), which moves every segment: R maps a v2 cut time to the
# same moment of the same source clip in the current cut.
with open('work/v0/segments_v2.json', encoding='utf-8') as _f:
    OLD = json.load(_f)


def R(t):
    o = OLD[0]
    for x in OLD:
        if x['frame'] / 30 <= t + 1e-3:
            o = x
    n = SEG[o['id']]
    return n['frame'] / 30 + (o['src_in'] + (t - o['frame'] / 30) - n['src_in'])


def S(t):
    return R(t - 2.566667)


HEAD = {}   # segment id -> head top y (from headpos.py), filled below if work/head.json exists
if os.path.exists('work/head.json'):
    with open('work/head.json', encoding='utf-8') as _f:
        HEAD = json.load(_f)


def seg_at(t):
    cur = SEGS[0]
    for s in SEGS:
        if s['frame'] / 30 <= t + 1e-3:
            cur = s
    return cur


GIRL_F = 'sepia(.18) saturate(.9) contrast(.93) brightness(1.05) hue-rotate(-5deg)'

# ------------------------------------------------------------------ motion graphic windows (chest band is theirs)
G_RM = (R(22.60), R(26.48))        # "you nak dapat RM10,000 sebulan dalam bisnis you"
G_PLAN = (R(30.00), R(37.74))      # "ambil planner you ... tulis kat dalam planner you, goal you"
G_TREE = (R(53.30), R(69.18))      # "achieve 10k ... berapa produk ... harga ... marketing"
G_TASK = (R(74.70), R(81.31))      # "task yang pertama ... task yang kedua, buat video"
G_PROG = (S(123.40), DUR)       # "move or progress ... small progress is still a progress"
GFX = [G_RM, G_PLAN, G_TREE, G_TASK, G_PROG]


def in_gfx(a, b):
    return any(a < gb - .05 and b > ga + .05 for ga, gb in GFX)


# ------------------------------------------------------------------ captions (what she actually said)
CAPS = [  # (start, text)   each chunk stays until the next one starts (or the end time in ENDS)
    (R(0.30), 'okey kejap,'), (R(0.91), 'awak ada impian,'), (R(2.15), 'awak ada angan-angan.'),
    (R(3.33), 'kenapa awak tak capai lagi'), (R(4.55), 'impian dan angan-angan awak?'),
    (R(7.23), 'sebenarnya, saya tahu,'), (R(8.67), 'awak bukannya tak motivasi'), (R(10.09), 'tapi awak tak tahu'),
    (R(11.51), 'apa nak buat selanjutnya'), (R(12.69), 'untuk mencapai tujuan awak.'), (R(14.91), 'dan itu okey.'),
    (R(15.93), 'sebab dalam video ni, saya akan beritahu'), (R(18.77), 'what to do next'), (R(19.63), 'to achieve your goal.'),
    (R(21.18), 'sebagai contoh kan,'), (R(22.68), 'you nak dapat RM10,000 sebulan'), (R(25.12), 'dalam bisnis you.'),
    (R(26.51), 'itu adalah goal you.'), (R(28.47), 'so next, apa you perlu buat adalah'), (R(30.09), 'ambil planner you.'),
    (R(32.01), 'and then ambil kertas ke apa kan.'), (R(34.95), 'tulis kat dalam planner you,'), (R(37.07), 'goal you.'),
    (R(37.76), 'apa you perlu buat adalah,'), (R(39.76), 'bukan tengok je goal tu hari-hari.'),
    (R(42.42), 'kalau tengok je, dia memang'), (R(43.52), 'tak akan bergerak.'), (R(44.84), 'you kena tahu exactly'),
    (R(47.40), 'what to do next.'),
    (R(48.93), 'so, apa yang awak perlu buat adalah'), (R(50.62), 'break down your goal.'),
    (R(52.52), 'tadi awak cakap yang awak nak'), (R(53.42), 'achieve 10k sebulan.'),
    (R(55.28), 'so, macam mana awak nak achieve that 10k?'), (R(57.54), 'berapa total produk yang awak perlu jual'),
    (R(60.58), 'dalam masa sebulan'), (R(61.88), 'untuk achieve that 10k?'), (R(64.86), 'lepas itu, berapa harga produk tersebut?'),
    (R(67.18), 'and then marketing,'), (R(68.10), 'apa yang awak nak buat?'),
    (R(69.20), "so, that's your big step."), (R(70.42), 'kemudian, you boleh pecahkan lagi'), (R(72.10), 'kepada baby step.'),
    (R(74.00), 'marketing apa?'), (R(74.74), 'mungkin, task yang pertama adalah,'), (R(76.86), 'decide nak guna marketing apa.'),
    (R(78.86), 'task yang kedua,'), (R(80.38), 'buat video.'),
    (R(81.40), 'bila awak dah tahu'), (R(82.95), 'what is your next action'), (R(84.93), 'towards your goal,'),
    (R(86.59), 'it becomes a bit more easier'), (R(88.73), 'untuk you achieve that goal.'), (R(91.25), 'sebab itu penting'),
    (R(92.11), 'untuk you break it down.'),
    (R(93.90), 'to be honest with you guys,'), (R(96.78), 'I am so bad,'), (R(97.50), 'so, so bad'), (R(99.92), 'at breaking down'), (R(100.96), 'my goal before.'),
    (S(104.82), 'so, kalau you ada goal'), (S(105.86), 'and you tak dapat nak achieve your goal lagi,'),
    (S(109.14), 'you tak tahu kenapa goal you tak bergerak pun'), (S(111.04), 'sampai you rasa macam malas lah,'),
    (S(114.44), 'macam tu sekali.'),
    (S(115.48), 'actually,'), (S(116.48), 'jangan padam lagi goal you tu.'), (S(118.22), 'you just need to figure out'),
    (S(120.76), 'what are the next actions'), (S(122.50), 'untuk you move'), (S(124.04), 'or progress towards that goal.'),
    (S(126.78), 'okay, remember,'), (S(127.80), 'small progress is still a progress.'),
]
ENDS = {R(0.30): R(0.88), R(14.91): R(15.90), R(19.63): R(21.10), R(25.12): R(26.38), R(37.07): R(37.60), R(47.40): R(48.90), R(68.10): R(69.08), R(80.38): R(81.30),
        R(92.11): R(93.85), R(100.96): R(101.95), S(114.44): S(115.20), S(127.80): DUR}
TOP_CAP, LOW_CAP = 236, 1300


def captions():
    html, tw = [], []
    for k, (a, text) in enumerate(CAPS):
        b = ENDS.get(a, CAPS[k + 1][0] if k + 1 < len(CAPS) else DUR)
        words = text.split(' ')
        top = TOP_CAP if in_gfx(a, b) else LOW_CAP
        cid = f'c{k}'
        spans = ' '.join(f'<span id="{cid}-{i}" class="gw">{w}</span>' for i, w in enumerate(words))
        html.append(f'<div id="{cid}" class="cap" style="top:{top}px">{spans}</div>')
        span = max(.2, min(b - a - .25, .32 * len(words)))
        tw.append(f"gsap.set('#{cid} .gw',{{autoAlpha:0}});")
        for i in range(len(words)):
            t = a - .04 + span * i / max(1, len(words))
            tw.append(f"tl.fromTo('#{cid}-{i}',{{autoAlpha:0,y:14,filter:'blur(6px)'}},{{autoAlpha:1,y:0,filter:'blur(0px)',"
                      f"duration:.26,ease:'power2.out',immediateRender:false}},{t:.3f});")
        if b < DUR - .01:
            tw.append(f"tl.to('#{cid}',{{autoAlpha:0,duration:.12}},{b - .12:.3f});")
            tw.append(f"tl.set('#{cid}',{{autoAlpha:0}},{b:.3f});")
    return html, tw


# ------------------------------------------------------------------ yellow serif punch words, behind her head
SERIF = [  # (t, end, text, size)
    (R(1.25), R(2.10), 'impian', 190), (R(2.58), R(3.30), 'angan-angan', 150), (R(15.05), R(15.90), 'itu okey.', 170),
    (R(18.74), R(21.10), 'what to do next', 120), (R(39.90), R(42.38), 'tengok je', 170),
    (R(46.20), R(48.90), 'exactly.', 170), (R(50.58), R(52.48), 'break down', 160),
    (R(69.66), R(70.40), 'big step', 160), (R(72.56), R(74.00), 'baby step', 160), (R(83.88), R(86.50), 'next action', 150), (R(92.65), R(93.85), 'break it down', 130),
    (R(97.48), R(99.88), 'so bad', 180), (S(116.44), S(118.15), 'jangan padam', 140),
]


def head_top(t, b):
    """highest point her head reaches across every segment the word spans"""
    ids = [x['id'] for x in SEGS if x['frame'] / 30 < b and (x['frame'] + x['frames']) / 30 > t + .05]
    return min(HEAD.get(i, 470) for i in ids)


def serif_place(t, b, size):
    """-> (top, size, front). Behind the head with the baseline just above her hijab, so the rounded top only takes
    the descenders; if that does not fit under the 220 safe line even at 110px, the word goes in front instead."""
    ht = head_top(t, b)
    fit = (ht - 222) / .77
    if fit >= 110:
        size = min(size, int(fit))
        return round(ht - .77 * size), size, False
    return 230, size, True


def serif():
    back, front, tw = [], [], []
    for k, (t, b, text, size) in enumerate(SERIF):
        sid = f's{k}'
        top, size, fr = serif_place(t, b, size)
        chars = ''.join(f'<span class="ch">{"&nbsp;" if c == " " else c}</span>' for c in text)
        el = f'<div id="{sid}" class="serif{" front" if fr else ""}" style="top:{top}px;font-size:{size}px">{chars}</div>'
        (front if fr else back).append(el)
        tw += [f"gsap.set('#{sid}',{{autoAlpha:0}});",
               f"tl.set('#{sid}',{{autoAlpha:1}},{t - .04:.3f});",
               f"tl.fromTo('#{sid} .ch',{{autoAlpha:0,y:30,filter:'blur(10px)'}},{{autoAlpha:1,y:0,filter:'blur(0px)',duration:.42,"
               f"ease:'power3.out',stagger:.03,immediateRender:false}},{t - .04:.3f});",
               f"tl.to('#{sid}',{{autoAlpha:0,y:-10,filter:'blur(8px)',duration:.16,ease:'power2.in'}},{b - .16:.3f});",
               f"tl.set('#{sid}',{{autoAlpha:0}},{b:.3f});"]
    # tiny twinkling sparkles beside a few of them (front layer)
    sparks = []
    for k, (x, y, sz, t, b) in enumerate([(120, 300, 54, R(1.40), R(3.30)), (900, 260, 36, R(1.55), R(3.30)), (930, 330, 44, R(15.15), R(15.90)),
                                          (110, 280, 46, R(46.30), R(48.90)), (920, 250, 40, R(97.60), R(99.88)),
                                          (130, 350, 34, R(97.72), R(99.88)), (930, 300, 44, R(72.66), R(74.00))]):
        sparks.append(f'<div id="sp{k}" class="spark" style="left:{x}px;top:{y}px;font-size:{sz}px">&#10022;</div>')
        tw += [f"gsap.set('#sp{k}',{{autoAlpha:0,scale:0}});",
               f"tl.to('#sp{k}',{{autoAlpha:1,scale:1,rotation:90,duration:.35,ease:'back.out(2.5)'}},{t:.3f});",
               *([f"tl.to('#sp{k}',{{scale:.65,duration:.45,yoyo:true,repeat:1,ease:'sine.inOut'}},{t + .35:.3f});"] if b - t > 1.5 else []),
               f"tl.to('#sp{k}',{{autoAlpha:0,scale:0,duration:.16}},{b - .16:.3f});",
               f"tl.set('#sp{k}',{{autoAlpha:0}},{b:.3f});"]
    return back, front + sparks, tw


def show(sel, a, b, frm="{autoAlpha:0,y:50,scale:.9}", to="autoAlpha:1,y:0,scale:1"):
    return [f"gsap.set('{sel}',{frm});",
            f"tl.to('{sel}',{{{to},duration:.5,ease:'back.out(1.5)'}},{a:.3f});",
            f"tl.to('{sel}',{{autoAlpha:0,y:-30,scale:.94,duration:.2,ease:'power2.in'}},{b - .2:.3f});",
            f"tl.set('{sel}',{{autoAlpha:0}},{b:.3f});"] if b < DUR - .01 else [
            f"gsap.set('{sel}',{frm});", f"tl.to('{sel}',{{{to},duration:.5,ease:'back.out(1.5)'}},{a:.3f});"]


# ------------------------------------------------------------------ motion graphics
def g_rm():
    a, b = G_RM
    steps = [0, 400, 1200, 2500, 4000, 5600, 7000, 8200, 9100, 9700, 10000]
    t0, t1 = R(23.30), R(24.40)
    nums = ''.join(f'<span id="rmn{i}" class="rmn">RM{v:,}</span>' for i, v in enumerate(steps))
    html = [f'<div id="grm" class="card pill" style="left:190px;top:1200px;width:700px">'
            f'<div class="hand">goal bulan ni</div><div class="rmrow">{nums}<span class="per">/ sebulan</span></div>'
            f'<div class="bar"><div id="rmfill" class="fill"></div></div></div>']
    tw = show('#grm', a, b) + ["gsap.set('.rmn',{autoAlpha:0});", "gsap.set('#rmn0',{autoAlpha:1});",
                               "gsap.set('#rmfill',{scaleX:0});",
                               f"tl.to('#rmfill',{{scaleX:1,duration:{t1 - t0:.2f},ease:'power2.out'}},{t0:.3f});"]
    for i in range(1, len(steps)):
        t = t0 + (t1 - t0) * i / (len(steps) - 1)
        tw += [f"tl.set('#rmn{i - 1}',{{autoAlpha:0}},{t:.3f});", f"tl.set('#rmn{i}',{{autoAlpha:1}},{t:.3f});"]
    tw.append(f"tl.fromTo('#rmn{len(steps) - 1}',{{scale:1.18}},{{scale:1,duration:.4,ease:'back.out(3)',immediateRender:false}},{t1:.3f});")
    return html, tw


def g_plan():
    a, b = G_PLAN
    text = 'RM10k sebulan'
    chars = ''.join(f'<span id="pc{i}" class="pch">{"&nbsp;" if c == " " else c}</span>' for i, c in enumerate(text))
    holes = ''.join('<i></i>' for _ in range(7))
    html = [f'<div id="gplan" class="card paper" style="left:170px;top:1192px;width:740px;height:268px">'
            f'<div class="holes">{holes}</div><div class="plabel">MY GOAL</div><div class="pwrite">{chars}</div>'
            '<svg class="pline" width="520" height="40" viewBox="0 0 520 40"><path id="pul" d="M6 26 C 120 8, 300 34, 512 14" '
            'fill="none" stroke="#E0574F" stroke-width="7" stroke-linecap="round"/></svg>'
            '<div id="pstar" class="pstar">&#10022;</div></div>']
    tw = show('#gplan', a, b, frm="{autoAlpha:0,y:80,rotation:-4,scale:.9}", to="autoAlpha:1,y:0,rotation:-2,scale:1")
    tw += ["gsap.set('.pch',{autoAlpha:0});", "gsap.set('#pul',{strokeDasharray:560,strokeDashoffset:560});",
           "gsap.set('#pstar',{autoAlpha:0,scale:0});"]
    t0, t1 = R(34.95), R(36.70)
    for i in range(len(text)):
        tw.append(f"tl.set('#pc{i}',{{autoAlpha:1}},{t0 + (t1 - t0) * i / len(text):.3f});")
    tw += [f"tl.to('#pul',{{strokeDashoffset:0,duration:.5,ease:'power2.inOut'}},{R(37.00):.3f});",
           f"tl.to('#pstar',{{autoAlpha:1,scale:1,rotation:120,duration:.4,ease:'back.out(2.5)'}},{R(37.07):.3f});"]
    return html, tw


def g_strike():
    """red hand-drawn line through 'tengok je' (the serif word sits behind her head)"""
    k = [i for i, s in enumerate(SERIF) if s[2] == 'tengok je'][0]
    t, b, _, size = SERIF[k]
    top, size, front = serif_place(t, b, size)
    top += int(size * .55)
    fr = ' front' if front else ''
    html = [f'<svg id="gstrike" class="strike{fr}" style="top:{top}px" width="760" height="60" viewBox="0 0 760 60">'
            '<path id="stk" d="M10 40 C 200 20, 480 46, 750 18" fill="none" stroke="#E0574F" stroke-width="12" stroke-linecap="round"/></svg>']
    tw = ["gsap.set('#stk',{strokeDasharray:800,strokeDashoffset:800});", "gsap.set('#gstrike',{autoAlpha:0});",
          f"tl.set('#gstrike',{{autoAlpha:1}},{R(41.30):.3f});",
          f"tl.to('#stk',{{strokeDashoffset:0,duration:.35,ease:'power2.out'}},{R(41.30):.3f});",
          f"tl.set('#gstrike',{{autoAlpha:0}},{b:.3f});"]
    return html, tw


def g_tree():
    a, b = G_TREE
    chips = [('berapa produk?', R(57.50)), ('harga produk?', R(64.82)), ('marketing?', R(67.14))]
    xs = [75, 375, 675]
    html = ['<div id="gtree" class="tree">'
            '<div id="tnode" class="node">RM10k <em>/ sebulan</em></div>'
            '<svg class="tlines" width="1080" height="80" viewBox="0 0 1080 80">'
            + ''.join(f'<path id="tl{i}" d="M540 2 C 540 50, {x + 145} 30, {x + 145} 78" fill="none" stroke="{CREAM}" '
                      f'stroke-width="4" stroke-linecap="round" opacity=".85"/>' for i, x in enumerate(xs))
            + '</svg>'
            + ''.join(f'<div id="tc{i}" class="chip" style="left:{x}px"><b>{i + 1}</b>{c}</div>' for i, ((c, _), x) in enumerate(zip(chips, xs)))
            + '</div>']
    tw = ["gsap.set('#gtree',{autoAlpha:0});", f"tl.set('#gtree',{{autoAlpha:1}},{a:.3f});",
          "gsap.set('#tnode',{autoAlpha:0,scale:.6,y:30});",
          f"tl.to('#tnode',{{autoAlpha:1,scale:1,y:0,duration:.5,ease:'back.out(2)'}},{a + .05:.3f});",
          ]
    for i, (c, t) in enumerate(chips):
        tw += [f"gsap.set('#tl{i}',{{strokeDasharray:260,strokeDashoffset:260}});",
               f"tl.to('#tl{i}',{{strokeDashoffset:0,duration:.35,ease:'power2.out'}},{t - .25:.3f});",
               f"gsap.set('#tc{i}',{{autoAlpha:0,scale:.5,y:30}});",
               f"tl.to('#tc{i}',{{autoAlpha:1,scale:1,y:0,duration:.45,ease:'back.out(2.2)'}},{t:.3f});"]
    tw += [f"tl.to('#gtree',{{autoAlpha:0,y:-30,duration:.2,ease:'power2.in'}},{b - .2:.3f});", f"tl.set('#gtree',{{autoAlpha:0}},{b:.3f});"]
    return html, tw


def g_task():
    a, b = G_TASK
    rows = [('decide nak guna marketing apa', R(75.80), R(78.10)), ('buat video', R(78.86), R(80.80))]
    body = ''.join(f'<div id="tr{i}" class="trow"><span class="box"><svg width="40" height="40" viewBox="0 0 40 40">'
                   f'<path id="tk{i}" d="M8 21 L17 30 L33 11" fill="none" stroke="#2B2320" stroke-width="5" stroke-linecap="round" '
                   f'stroke-linejoin="round"/></svg></span><span class="tt"><small>task {i + 1}</small>{txt}</span></div>'
                   for i, (txt, _, _) in enumerate(rows))
    html = [f'<div id="gtask" class="card paper list" style="left:150px;top:1215px;width:780px">'
            f'{body}</div>']
    tw = show('#gtask', a, b, frm="{autoAlpha:0,y:80,rotation:3,scale:.9}", to="autoAlpha:1,y:0,rotation:1,scale:1")
    for i, (_, t, tick) in enumerate(rows):
        tw += [f"gsap.set('#tr{i}',{{autoAlpha:0,x:-30}});",
               f"tl.to('#tr{i}',{{autoAlpha:1,x:0,duration:.35,ease:'power3.out'}},{t:.3f});",
               f"gsap.set('#tk{i}',{{strokeDasharray:50,strokeDashoffset:50}});",
               f"tl.to('#tk{i}',{{strokeDashoffset:0,duration:.3,ease:'power2.out'}},{tick:.3f});",
               f"tl.to('#tr{i} .box',{{backgroundColor:'{YEL}',duration:.2}},{tick:.3f});"]
    return html, tw


def g_prog():
    a, _ = G_PROG
    html = ['<div id="gprog" class="card pill" style="left:150px;top:1238px;width:780px">'
            '<div class="prow"><span>progress</span><span id="pct0" class="pct">0%</span><span id="pct1" class="pct">12%</span>'
            '<span id="pct2" class="pct">35%</span></div>'
            '<div class="bar big"><div id="pfill" class="fill"></div></div>'
            '<div id="pnote" class="hand">small progress is still a progress &#10022;</div></div>']
    tw = show('#gprog', a, DUR) + [
        "gsap.set('#pfill',{scaleX:0});", "gsap.set(['#pct1','#pct2'],{autoAlpha:0});", "gsap.set('#pnote',{autoAlpha:0,y:16});",
        f"tl.to('#pfill',{{scaleX:.12,duration:.7,ease:'power2.out'}},{S(124.60):.3f});",
        f"tl.set('#pct0',{{autoAlpha:0}},{S(124.90):.3f});", f"tl.set('#pct1',{{autoAlpha:1}},{S(124.90):.3f});",
        f"tl.to('#pfill',{{scaleX:.35,duration:.8,ease:'back.out(1.6)'}},{S(127.80):.3f});",
        f"tl.set('#pct1',{{autoAlpha:0}},{S(128.10):.3f});", f"tl.set('#pct2',{{autoAlpha:1}},{S(128.10):.3f});",
        f"tl.to('#pnote',{{autoAlpha:1,y:0,duration:.5,ease:'power3.out'}},{S(128.00):.3f});"]
    return html, tw


def grades():
    tw = [f"gsap.set('.g',{{filter:'{GIRL_F}'}});"]
    for t in CUTS:
        tw.append(f"tl.fromTo('#stage',{{scale:1.04}},{{scale:1,duration:.32,ease:'power2.out',immediateRender:false}},{t:.3f});")
    return tw


SFX = ([('sparkle', R(1.25), .22), ('pop', R(2.58), .15), ('sparkle', R(15.05), .2), ('whoosh-short', R(18.70), .2),
        ('whoosh-short', G_RM[0], .25), ('click-soft', R(24.40), .5), ('whoosh-short', G_PLAN[0], .25), ('sparkle', R(37.07), .2),
        ('whoosh-short', R(41.28), .2), ('pop', R(46.20), .15), ('whoosh-short', R(50.55), .22),
        ('pop', R(53.35), .16), ('pop', R(57.50), .16), ('pop', R(64.82), .16), ('pop', R(67.14), .16), ('sparkle', R(72.56), .2),
        ('whoosh-short', G_TASK[0], .25), ('click', R(78.10), .6), ('click', R(80.80), .6), ('pop', R(83.88), .14),
        ('whoosh-short', R(92.60), .18), ('sparkle', R(97.48), .2), ('whoosh-short', S(116.40), .2),
        ('whoosh-short', G_PROG[0], .25), ('sparkle', S(128.00), .25)])
SFX_LEN = {'whoosh-short': .57, 'pop': .72, 'sparkle': 1.8, 'click': .3, 'click-soft': .37}
SFX_GAIN = 0.75


def audio():
    out, lanes = [], []
    for k, (name, t, vol) in enumerate(sorted(SFX, key=lambda x: x[1])):
        d = min(SFX_LEN[name], DUR - t)
        lane = next((i for i, end in enumerate(lanes) if end <= t), None)
        if lane is None:
            lanes.append(0); lane = len(lanes) - 1
        lanes[lane] = t + d
        out.append(f'<audio id="sfx{k}" src="assets/sfx/{name}.mp3" data-start="{t:.3f}" data-duration="{d:.3f}" '
                   f'data-track-index="{10 + lane}" data-volume="{vol * SFX_GAIN:.3f}"></audio>')
    return out


CSS = f'''
*{{margin:0;padding:0;box-sizing:border-box}}
html,body{{width:1080px;height:1920px;overflow:hidden;background:#000}}
#root{{position:relative;width:1080px;height:1920px;overflow:hidden;background:#000}}
#stage{{position:absolute;inset:0;transform-origin:50% 45%}}
.full{{position:absolute;inset:0;width:100%;height:100%;object-fit:cover}}
#bgv{{z-index:0}}
#cutwrap{{position:absolute;inset:0;z-index:4}}
.fx{{position:absolute;inset:0;pointer-events:none}}
#gwarm{{z-index:7;background:linear-gradient(180deg,rgba(255,226,200,.10),rgba(255,196,170,.16));mix-blend-mode:soft-light}}
#gvig{{z-index:7;background:radial-gradient(120% 70% at 50% 45%,rgba(255,255,255,0) 52%,rgba(60,35,25,.34) 100%)}}
#ggrad{{z-index:7;background:linear-gradient(180deg,rgba(60,35,25,.30) 0%,rgba(60,35,25,0) 26%,rgba(60,35,25,0) 58%,rgba(40,24,18,.55) 78%,rgba(40,24,18,.25) 100%)}}

.cap{{position:absolute;left:70px;right:130px;z-index:8;text-align:center;color:{CREAM};font:500 60px Inter;letter-spacing:-1px;
  line-height:1.16;text-shadow:0 2px 24px rgba(50,25,15,.75),0 1px 4px rgba(40,20,10,.5)}}
.gw{{display:inline-block}}
.serif{{position:absolute;left:0;right:0;z-index:3;text-align:center;color:{YEL};font-family:'Instrument Serif';font-style:italic;
  font-weight:400;line-height:.92;white-space:nowrap;letter-spacing:-.01em;text-shadow:0 8px 36px rgba(60,30,20,.45)}}
.serif .ch{{display:inline-block}}
.serif.front{{z-index:8}}
.strike.front{{z-index:8}}
.spark{{position:absolute;z-index:8;color:{YEL};line-height:1;text-shadow:0 0 18px rgba(250,230,122,.6)}}
.strike{{position:absolute;left:160px;z-index:3;filter:drop-shadow(0 4px 10px rgba(0,0,0,.25))}}

.card{{position:absolute;z-index:9;border-radius:34px;box-shadow:0 30px 70px rgba(40,20,12,.45),0 6px 16px rgba(40,20,12,.25)}}
.pill{{background:rgba(255,248,239,.94);padding:26px 40px 30px;color:#2B2320}}
.hand{{font:600 50px Caveat;color:#C2453E;line-height:1}}
.hand.dark{{color:#C2453E;margin-bottom:10px}}
.rmrow{{position:relative;height:112px;margin-top:4px}}
.rmn{{position:absolute;left:0;top:0;font:italic 400 116px 'Instrument Serif';color:#2B2320;line-height:1;transform-origin:0 70%}}
.per{{position:absolute;right:0;bottom:22px;font:500 40px Inter;color:#7A6A60}}
.bar{{height:16px;border-radius:99px;background:rgba(43,35,32,.12);overflow:hidden;margin-top:12px}}
.bar.big{{height:30px;margin:18px 0 18px}}
.fill{{height:100%;width:100%;border-radius:99px;background:linear-gradient(90deg,#F2C94C,{YEL});transform-origin:0 50%}}
.paper{{background:#FFFBF3 repeating-linear-gradient(180deg,rgba(0,0,0,0) 0 62px,rgba(120,150,190,.28) 62px 64px);
  padding:34px 40px 30px 96px;color:#2B2320}}
.holes{{position:absolute;left:28px;top:24px;bottom:24px;display:flex;flex-direction:column;justify-content:space-between}}
.holes i{{display:block;width:26px;height:26px;border-radius:50%;background:#3a2c28;box-shadow:inset 0 3px 5px rgba(0,0,0,.5)}}
.plabel{{font:600 30px Inter;letter-spacing:.24em;color:#9C8A80}}
.pwrite{{font:600 100px Caveat;color:#2B2320;line-height:1.1;margin-top:10px;white-space:nowrap}}
.pch{{display:inline-block}}
.pline{{position:absolute;left:96px;top:196px}}
.pstar{{position:absolute;right:40px;top:40px;font-size:64px;color:#E0B83A}}
.tree{{position:absolute;left:0;top:1212px;width:1080px;height:280px;z-index:9}}
.node{{position:absolute;left:315px;width:450px;top:0;text-align:center;padding:10px 0 14px;border-radius:99px;background:{YEL};color:#2B2320;
  font:italic 400 76px 'Instrument Serif';line-height:1;box-shadow:0 20px 50px rgba(40,20,12,.4)}}
.node em{{font:500 34px Inter;font-style:normal;color:#5b4a40}}
.tlines{{position:absolute;left:0;top:100px}}
.chip{{position:absolute;top:172px;width:290px;text-align:center;padding:18px 8px;border-radius:26px;background:rgba(255,248,239,.95);
  color:#2B2320;font:600 31px Inter;letter-spacing:-.5px;box-shadow:0 18px 40px rgba(40,20,12,.38);white-space:nowrap}}
.chip b{{display:inline-block;width:42px;height:42px;line-height:42px;border-radius:50%;background:#2B2320;color:{YEL};font:600 26px Inter;
  margin-right:10px;vertical-align:2px}}
.tbig{{position:absolute;left:0;right:0;top:-150px;text-align:center;font:italic 400 130px 'Instrument Serif';color:{YEL};
  text-shadow:0 8px 36px rgba(60,30,20,.5)}}
.list{{padding:18px 40px 18px 96px;height:auto}}
.trow{{display:flex;align-items:center;gap:22px;height:100px}}
.box{{flex:none;width:56px;height:56px;border-radius:14px;border:4px solid #2B2320;display:flex;align-items:center;justify-content:center}}
.tt{{font:600 38px Inter;letter-spacing:-.8px;line-height:1.1}}
.tt small{{display:block;font:600 24px Inter;letter-spacing:.2em;text-transform:uppercase;color:#9C8A80}}
.prow{{display:flex;justify-content:space-between;align-items:baseline;position:relative;font:600 34px Inter;letter-spacing:.18em;
  text-transform:uppercase;color:#7A6A60}}
.pct{{position:absolute;right:0;top:-12px;font:italic 400 76px 'Instrument Serif';letter-spacing:0;color:#2B2320;text-transform:none}}
#pnote{{font-size:54px;text-align:center}}
'''

SAFE_GUIDE = ('<div style="position:absolute;inset:0;z-index:99;pointer-events:none">'
              '<div style="position:absolute;left:0;right:0;top:0;height:220px;background:rgba(255,0,0,.28)"></div>'
              '<div style="position:absolute;left:0;right:0;top:1470px;bottom:0;background:rgba(255,0,0,.28)"></div>'
              '<div style="position:absolute;left:0;width:35px;top:220px;height:1250px;background:rgba(255,0,0,.28)"></div>'
              '<div style="position:absolute;right:0;width:35px;top:220px;height:935px;background:rgba(255,0,0,.28)"></div>'
              '<div style="position:absolute;right:0;width:100px;top:1155px;height:315px;background:rgba(255,0,0,.28)"></div></div>')


def build():
    c_html, c_tw = captions()
    s_back, s_sp, s_tw = serif()
    st_html, st_tw = g_strike()
    (s_sp if 'front' in st_html[0] else s_back).extend(st_html)
    parts = [g_rm(), g_plan(), (st_html[:0], st_tw), g_tree(), g_task(), g_prog()]
    g_html = [h for p in parts for h in p[0]]
    tweens = grades() + s_tw + c_tw + [t for p in parts for t in p[1]]
    nl = '\n'
    return f'''<!doctype html>
<html lang="ms" data-resolution="portrait">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=1080, height=1920" />
<link rel="stylesheet" href="assets/fonts/fonts.css" />
<script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
<style>{CSS}</style>
</head>
<body>
<div id="root" data-composition-id="main" data-start="0" data-duration="{DUR:.3f}" data-width="1080" data-height="1920">
  <audio id="bga" src="assets/aroll.mp4" data-start="0" data-media-start="0" data-duration="{DUR:.3f}" data-track-index="2" data-volume="1"></audio>
{nl.join(audio())}
  <div id="stage">
    <video id="bgv" class="full g" src="assets/aroll.mp4" muted playsinline data-start="0" data-media-start="0" data-duration="{DUR:.3f}" data-track-index="0"></video>
{nl.join(s_back)}
    <div id="cutwrap"><video id="cut" class="full g" src="assets/subject.webm" muted playsinline data-start="0" data-media-start="0" data-duration="{DUR:.3f}" data-track-index="1"></video></div>
  </div>
  <div id="gwarm" class="fx"></div><div id="gvig" class="fx"></div><div id="ggrad" class="fx"></div>
{nl.join(s_sp)}
{nl.join(c_html)}
{nl.join(g_html)}
{SAFE_GUIDE if SAFE else ''}
</div>
<script>
const tl = gsap.timeline({{ paused: true }});
{nl.join(tweens)}
tl.set({{}}, {{}}, {DUR:.3f});
window.__timelines["main"] = tl;
</script>
</body>
</html>
'''


def layer(html):
    """strip media and the other layer; transparent page. back = words under the cutout, front = everything above"""
    import re
    html = re.sub(r'\s*<audio[^>]*></audio>', '', html)
    html = re.sub(r'\s*<video[^>]*></video>', '', html)
    html = html.replace('<div id="cutwrap"></div>', '')
    html = html.replace('background:#000}}', 'background:transparent}}').replace('background:#000}', 'background:transparent}')
    html = html.replace('<div id="gwarm" class="fx"></div>', '')
    if LAYER == 'back':
        html = html.replace('</style>', '#root>*:not(#stage){display:none!important}</style>')
    else:
        html = html.replace('</style>', '#stage{display:none!important}</style>')
    return html


out = build()
if LAYER:
    out = layer(out)
    if os.environ.get('TEST'):
        out = out.replace(f'data-duration="{DUR:.3f}"', 'data-duration="3.000"', 1)
with open(f'{LAYER}.html' if LAYER else 'index.html', 'w', encoding='utf-8', newline='\n') as _f:
    _f.write(out)
print(f'wrote index.html {DUR:.3f}s  {len(CUTS)} cuts  {len(CAPS)} caption chunks  head data: {bool(HEAD)}')
