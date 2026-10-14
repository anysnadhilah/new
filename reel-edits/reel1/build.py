#!/usr/bin/env python3
"""reel1: "plan terbalik" (quit your 9-5 with side income), cool girl look throughout.

Built from the /video-edit template machinery (orbit, cool girl type, grades, audio lanes, SAFE_GUIDE, frame-exact
cut times from segments.json). Content is new:
  captions      every spoken phrase, calm lowercase Inter in the chest band, word-by-word (from words.json, fixed by hand)
  punch         Instrument Serif italic in butter yellow in the band above her head; behind her head where a cutout exists
  cutouts       only four sections are cut out (cut/<name>/assets/subject.webm): hook, plan, ideas, dreams
  graphics      9-5 strike, reverse-arrow note, step chips 01/02/03, RM counter card, side-income orbit,
                milestone checklist, work-backward ladder

PY build.py            writes index.html
PY build.py --safe     same + red Instagram safe-zone guide (snapshots only)
"""
import json
import math
import os
import shutil
import subprocess
import sys

SAFE = '--safe' in sys.argv or bool(os.environ.get('SAFE'))
DUR = float(subprocess.run([shutil.which('ffprobe') or 'ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries',
                            'stream=duration', '-of', 'csv=p=0', 'assets/aroll.mp4'],
                           capture_output=True, encoding='utf-8', errors='replace').stdout.strip().split(',')[0])
YEL = '#FAE67A'
CREAM = '#FFF8EF'
with open('segments.json', encoding='utf-8') as _f:
    SEGL = json.load(_f)
SEG = {s['id']: s for s in SEGL}
T = {k: s['frame'] / 30 - .002 if s['frame'] else 0.0 for k, s in SEG.items()}
END = {k: (s['frame'] + s['frames']) / 30 - .002 for k, s in SEG.items()}
CUTS = [T[s['id']] for s in SEGL[1:]]
with open('words.json', encoding='utf-8') as _f:
    WORDS = json.load(_f)


def kw(text, lo, hi=None):
    """start time of the first word containing `text` inside [lo, hi]"""
    hi = DUR if hi is None else hi
    for w in WORDS:
        if lo - .05 <= w['start'] <= hi and text.lower() in w['text'].lower():
            return w['start']
    raise SystemExit(f'word {text!r} not found in {lo:.2f}-{hi:.2f}')


# ------------------------------------------------------------------ captions
# (segment id, phrase list). Each phrase: text as said (fixed by hand), words matched to words.json in order.
from captions import PHRASES  # noqa: E402  (generated from words.json, then corrected by hand)

CAP_BOTTOM = 470          # caption block's bottom edge sits at y = 1920 - 470 = 1450 (safe line 1470)


def captions():
    html, tw = [], []
    for p, (a, b, words) in enumerate(PHRASES):
        spans = []
        for k, (t, txt) in enumerate(words):
            gid = f'cp{p}-{k}'
            cls = 'gw hl' if txt.startswith('*') else 'gw'
            spans.append(f'<span id="{gid}" class="{cls}">{txt.lstrip("*")}</span>')
            tw.append(f"tl.fromTo('#{gid}',{{autoAlpha:0,y:14}},{{autoAlpha:1,y:0,duration:.24,ease:'power2.out',immediateRender:false}},{max(a, t - .04):.3f});")
        html.append(f'<div id="cp{p}" class="cap">{" ".join(spans)}</div>')
        tw.append(f"gsap.set('#cp{p} .gw',{{autoAlpha:0}});")
        if b < DUR - .01:
            tw.append(f"tl.to('#cp{p}',{{autoAlpha:0,duration:.12}},{b - .12:.3f});")
            tw.append(f"tl.set('#cp{p}',{{autoAlpha:0}},{b:.3f});")
    return html, tw


# ------------------------------------------------------------------ punch words (serif italic, top band)
CUTOUT = {  # name -> (start segment, end segment) ; cut/<name>/assets/subject.webm covers exactly those frames
    'hook': ('hook', 'hook2'), 'plan': ('plan', 'plan'), 'ideas': ('ideas', 'affil'), 'dreams': ('planner2', 'planner2')}
CUT_SPAN = {n: (T[a], END[b]) for n, (a, b) in CUTOUT.items()}


def has_cutout(t0, t1):
    return any(a - .01 <= t0 and t1 <= b + .01 for a, b in CUT_SPAN.values())


def punches():
    P = [  # (t, end, text, size, top) ; behind the head automatically when the whole span has a cutout
        (kw('9', T['hook'], END['hook']), END['hook'], '9-5?', 230, 205),
        (kw('side', T['hook2'], END['hook2']), END['hook2'], 'side income', 150, 238),
        (kw('years', T['amount'], END['amount']) - .1, END['amount'], 'for years to come', 120, 250),
        (kw('masalah', T['problem'], END['problem']), END['problem'], 'tapi masalahnya...', 120, 250),
        (kw('impian', T['plan'], END['plan']), kw('plan', T['plan'], END['plan']) - .1, 'impian', 170, 215),
        (kw('plan', T['plan'], END['plan']), END['plan'], 'plan terbalik', 170, 215),
        (kw('resign', T['first'], END['first']), END['first'], 'resign.', 150, 238),
        (kw('stability', T['course'], END['course']) - .1, kw('Sebab', T['course'], END['course']) - .05, 'financial stability', 112, 255),
        (kw('consistent', T['consist'], END['consist']) - .1, END['consist'], 'consistent.', 150, 238),
        (kw('everything', T['cta'], END['cta']) - .15, kw('just', T['cta'], END['cta']) - .3, 'everything today?', 120, 250),
        (kw('next', T['cta'], END['cta']) - .1, kw('target', T['cta'], END['cta']) - .1, 'next action step', 120, 250),
        (kw('dreams', T['cta'], END['cta']) - .1, DUR, 'your dreams.', 150, 238),
        (kw('power', T['planner'], END['planner']), END['planner'], 'power planner', 140, 240),
        (kw('big', T['planner2'], END['planner2']), kw('backward', T['planner2'], END['planner2']) - .15, 'big dreams', 170, 215),
    ]
    back, front, tw = [], [], []
    for k, (t, b, text, size, top) in enumerate(P):
        pid = f'pw{k}'
        behind = has_cutout(t, b)
        chars = ''.join(f'<span class="mk"><span class="ch">{"&nbsp;" if c == " " else c}</span></span>' for c in text)
        (back if behind else front).append(f'<div id="{pid}" class="punch" style="top:{top}px;font-size:{size}px">{chars}</div>')
        tw += [f"gsap.set('#{pid}',{{autoAlpha:0}});",
               f"tl.set('#{pid}',{{autoAlpha:1}},{t - .04:.3f});",
               f"tl.fromTo('#{pid} .ch',{{yPercent:110,autoAlpha:0}},{{yPercent:0,autoAlpha:1,duration:.55,ease:'expo.out',stagger:.025,immediateRender:false}},{t - .04:.3f});",
               f"tl.fromTo('#{pid}',{{scale:1.05,filter:'blur(6px)'}},{{scale:1,filter:'blur(0px)',duration:.4,ease:'power3.out',immediateRender:false}},{t - .04:.3f});"]
        if b < DUR - .01:
            if b - t < .8:
                tw.append(f"tl.set('#{pid}',{{autoAlpha:0}},{b:.3f});")
            else:
                tw += [f"tl.to('#{pid}',{{autoAlpha:0,y:-12,filter:'blur(8px)',duration:.16,ease:'power2.in'}},{b - .16:.3f});",
                       f"tl.set('#{pid}',{{autoAlpha:0}},{b:.3f});"]
    return back, front, tw


def sparkles():
    S = [  # (x, y, size, t, end)
        (900, 300, 44, kw('9', T['hook'], END['hook']) + .2, END['hook']),
        (130, 250, 30, kw('9', T['hook'], END['hook']) + .35, END['hook']),
        (940, 270, 40, kw('plan', T['plan'], END['plan']) + .3, END['plan']),
        (90, 360, 30, kw('plan', T['plan'], END['plan']) + .45, END['plan']),
        (930, 260, 40, kw('power', T['planner'], END['planner']) + .3, END['planner']),
        (110, 300, 30, kw('power', T['planner'], END['planner']) + .5, END['planner']),
        (950, 280, 44, kw('dreams', T['cta'], END['cta']) + .2, DUR),
        (100, 330, 30, kw('dreams', T['cta'], END['cta']) + .35, DUR),
    ]
    html, tw = [], []
    for k, (x, y, sz, t, b) in enumerate(S):
        html.append(f'<div id="sp{k}" class="spark" style="left:{x}px;top:{y}px;font-size:{sz}px">&#10022;</div>')
        tw += [f"gsap.set('#sp{k}',{{autoAlpha:0,scale:0}});",
               f"tl.to('#sp{k}',{{autoAlpha:1,scale:1,rotation:90,duration:.35,ease:'back.out(2.5)'}},{t:.3f});",
               f"tl.to('#sp{k}',{{scale:.65,duration:.45,yoyo:true,repeat:3,ease:'sine.inOut'}},{t + .35:.3f});"]
        if b < DUR - .01:
            tw += [f"tl.to('#sp{k}',{{autoAlpha:0,duration:.12}},{b - .12:.3f});", f"tl.set('#sp{k}',{{autoAlpha:0}},{b:.3f});"]
    return html, tw


# ------------------------------------------------------------------ graphics
def strike_95():
    """a hand-drawn yellow strike through the '9-5?' punch on 'quit'"""
    t = kw('quit', T['hook'], END['hook'])
    html = ['<svg id="strike" class="ink" viewBox="0 0 560 90" style="left:250px;top:300px;width:560px;height:90px">'
            '<path d="M10 60 C 140 30, 300 70, 550 22" fill="none" stroke="#FAE67A" stroke-width="14" stroke-linecap="round" '
            'pathLength="1" stroke-dasharray="1" stroke-dashoffset="1"/></svg>']
    tw = ["gsap.set('#strike',{autoAlpha:0});", f"tl.set('#strike',{{autoAlpha:1}},{t:.3f});",
          f"tl.fromTo('#strike path',{{strokeDashoffset:1}},{{strokeDashoffset:0,duration:.35,ease:'power2.out',immediateRender:false}},{t:.3f});",
          f"tl.set('#strike',{{autoAlpha:0}},{END['hook']:.3f});"]
    return html, tw


def reverse_note():
    """'plan terbalik': handwritten note on the seat with a looping arrow drawn backwards"""
    t = kw('terbalik', T['plan'], END['plan'])
    html = ['<div id="rnote" class="note" style="left:745px;top:560px">dari impian,<br>ke hari ini</div>',
            '<svg id="rarrow" class="ink" viewBox="0 0 220 220" style="left:770px;top:690px;width:220px;height:220px">'
            '<path d="M180 30 C 230 120, 120 200, 60 150 C 10 110, 60 50, 110 90" fill="none" stroke="#FAE67A" stroke-width="8" '
            'stroke-linecap="round" pathLength="1" stroke-dasharray="1" stroke-dashoffset="1"/>'
            '<path d="M92 62 L 112 92 L 78 100" fill="none" stroke="#FAE67A" stroke-width="8" stroke-linecap="round" stroke-linejoin="round" opacity="0" class="head"/></svg>']
    b = END['plan']
    tw = ["gsap.set(['#rnote','#rarrow'],{autoAlpha:0});",
          f"tl.fromTo('#rnote',{{autoAlpha:0,y:16,rotation:-4}},{{autoAlpha:1,y:0,rotation:-4,duration:.4,ease:'power2.out',immediateRender:false}},{t:.3f});",
          f"tl.set('#rarrow',{{autoAlpha:1}},{t + .15:.3f});",
          f"tl.fromTo('#rarrow path',{{strokeDashoffset:1}},{{strokeDashoffset:0,duration:.7,ease:'power2.inOut',immediateRender:false}},{t + .15:.3f});",
          f"tl.to('#rarrow .head',{{opacity:1,duration:.1}},{t + .8:.3f});",
          f"tl.to(['#rnote','#rarrow'],{{autoAlpha:0,duration:.14}},{b - .14:.3f});", f"tl.set(['#rnote','#rarrow'],{{autoAlpha:0}},{b:.3f});"]
    return html, tw


def step_chips():
    """01 / 02 / 03 pills on each step, top-left over the roof lining"""
    S = [('01', 'tentukan amount', kw('First', T['first'], END['first']), END['example']),
         ('02', 'apa you boleh bina', T['second'] + .05, END['affil']),
         ('03', 'small milestone', kw('third', T['third'], END['third2']), END['baby'])]
    html, tw = [], []
    for k, (n, lab, a, b) in enumerate(S):
        html.append(f'<div id="chip{k}" class="chip"><span class="n">{n}</span><span class="l">{lab}</span></div>')
        tw += [f"gsap.set('#chip{k}',{{autoAlpha:0}});",
               f"tl.fromTo('#chip{k}',{{autoAlpha:0,x:-40,scale:.9}},{{autoAlpha:1,x:0,scale:1,duration:.45,ease:'back.out(1.6)',immediateRender:false}},{a:.3f});",
               f"tl.to('#chip{k}',{{autoAlpha:0,x:-20,duration:.16}},{b - .16:.3f});", f"tl.set('#chip{k}',{{autoAlpha:0}},{b:.3f});"]
    return html, tw


def money_card():
    """RM counter on the red seat: 0 -> 20,000 on 'RM20,000', struck on 'reducekan', then 5,000"""
    a = kw('RM20', T['example'], END['example'])
    r = kw('reduce', T['example'], END['example'])
    f5 = kw('RM5', T['example'], END['example'])
    b = END['example']

    def digits(cid, val, t0, dur=.9, steps=18):
        # one span per value revealed with tl.set (no onUpdate text tricks)
        h, w = [], []
        for i in range(steps + 1):
            v = round(val * (1 - (1 - i / steps) ** 3) / 100) * 100
            h.append(f'<span id="{cid}{i}" class="num">RM{v:,}</span>')
            w.append(f"tl.set('#{cid}{i}',{{display:'inline'}},{t0 + dur * i / steps:.3f});")
            if i < steps:
                w.append(f"tl.set('#{cid}{i}',{{display:'none'}},{t0 + dur * (i + 1) / steps:.3f});")
        return h, w

    h20, w20 = digits('m20_', 20000, a)
    h5, w5 = digits('m5_', 5000, f5)
    html = [f'<div id="mcard" class="mcard"><div class="lbl">side income target</div>'
            f'<div class="row" id="mrow20"><div class="nums">{"".join(h20)}</div>'
            f'<svg id="mstrike" viewBox="0 0 100 10" preserveAspectRatio="none"><line x1="0" y1="5" x2="100" y2="5" stroke="#FAE67A" '
            f'stroke-width="5" pathLength="1" stroke-dasharray="1" stroke-dashoffset="1"/></svg></div>'
            f'<div class="row" id="mrow5"><div class="nums y">{"".join(h5)}</div></div>'
            f'<div class="per">sebulan</div></div>']
    tw = ["gsap.set('#mcard',{autoAlpha:0});", "gsap.set('#mcard .num',{display:'none'});", "gsap.set('#mrow5',{autoAlpha:0});",
          f"tl.fromTo('#mcard',{{autoAlpha:0,y:40,scale:.9,rotation:3}},{{autoAlpha:1,y:0,scale:1,rotation:3,duration:.5,ease:'back.out(1.5)',immediateRender:false}},{a - .3:.3f});",
          f"tl.fromTo('#mstrike line',{{strokeDashoffset:1}},{{strokeDashoffset:0,duration:.35,ease:'power2.out',immediateRender:false}},{r:.3f});",
          f"tl.to('#mrow20',{{opacity:.45,duration:.3}},{r + .2:.3f});",
          f"tl.fromTo('#mrow5',{{autoAlpha:0,y:16}},{{autoAlpha:1,y:0,duration:.35,ease:'power2.out',immediateRender:false}},{f5 - .15:.3f});",
          f"tl.to('#mcard',{{autoAlpha:0,y:-20,duration:.18}},{b - .18:.3f});", f"tl.set('#mcard',{{autoAlpha:0}},{b:.3f});"] + w20 + w5
    return html, tw


# side-income ideas orbit around her on "maybe you nak start jual Canva template ... affiliate"
IDEAS = [('Canva', 'template', 'Canva'), ('PDF', 'ebook', 'PDF'), ('Etsy', 'shop', 'Etsy'), ('Instagram', 'shop', 'Instagram'),
         ('affiliate', 'link', 'affiliate')]
CX, CY, RX, RY = 510, 1185, 350, 85
TW_, TH_ = 230, 120
REV, STEP = 6.0, 0.1


def orbit():
    a, b = T['ideas'] + .15, END['affil']
    n = len(IDEAS)
    pops = [kw(key, T['ideas'], END['affil']) for _, _, key in IDEAS]
    html, tw = [], []
    for i, (big, small, _) in enumerate(IDEAS):
        for side in ('b', 'f'):
            html.append(f'<div id="{side}{i}" class="orb {side}"><div class="pop"><div class="itile"><div class="ib">{big}</div>'
                        f'<div class="is">{small}</div></div></div></div>')
        frames, t = [], a
        while t <= b + 1e-6:
            th = 2 * math.pi * ((t - a) / REV) + i * 2 * math.pi / n + 0.35
            s = math.sin(th)
            frames.append((t, CX + RX * math.cos(th), CY + RY * s, 0.72 + 0.28 * (s + 1) / 2, s))
            t = round(t + STEP, 4)
        for side in ('b', 'f'):
            sel = f'#{side}{i}'
            vis = (lambda s: 1 if s > 0 else 0) if side == 'f' else (lambda s: 0 if s > 0 else 1)
            t0, x0, y0, sc0, s0 = frames[0]
            tw.append(f"gsap.set('{sel}',{{xPercent:-50,yPercent:-50,x:{x0:.1f},y:{y0:.1f},scale:{sc0:.3f},autoAlpha:0}});")
            tw.append(f"tl.set('{sel}',{{autoAlpha:{vis(s0)}}},{t0:.3f});")
            kf = ','.join(f"{{x:{x:.1f},y:{y:.1f},scale:{sc:.3f},autoAlpha:{vis(s)},duration:{STEP},ease:'none'}}"
                          for _, x, y, sc, s in frames[1:])
            tw.append(f"tl.to('{sel}',{{keyframes:[{kf}]}},{t0:.3f});")
            tw.append(f"tl.set('{sel}',{{autoAlpha:0}},{b:.3f});")
            tw.append(f"gsap.set('{sel} .pop',{{scale:0}});")
            tw.append(f"tl.to('{sel} .pop',{{scale:1,duration:.45,ease:'back.out(1.8)'}},{pops[i] - .05:.3f});")
            tw.append(f"tl.to('{sel} .pop',{{scale:0,duration:.2,ease:'power2.in'}},{b - .24 + i * .01:.3f});")
    return html, tw, pops


def milestones():
    """checklist card on the seat: launch your first product -> this week's baby step"""
    a = kw('milestone', T['third2'], END['third2'])
    l1 = kw('launch', T['launch'], END['launch'])
    bb = kw('baby', T['baby'], END['baby'])
    mg = kw('minggu', T['baby'], END['baby'])
    b = END['baby']
    items = [('m0', 'big dream', a), ('m1', 'launch product', l1), ('m2', 'baby step', bb), ('m3', 'minggu ni', mg)]
    rows = ''.join(f'<div class="mi" id="{i}"><span class="box"><svg viewBox="0 0 24 24"><path d="M5 12.5 L10 17 L19 7" fill="none" '
                   f'stroke="#2b1d16" stroke-width="3.2" stroke-linecap="round" stroke-linejoin="round" pathLength="1" '
                   f'stroke-dasharray="1" stroke-dashoffset="1"/></svg></span><span>{lab}</span></div>' for i, lab, _ in items)
    html = [f'<div id="mlist" class="mlist"><div class="lbl">small milestones</div>{rows}</div>']
    tw = ["gsap.set('#mlist',{autoAlpha:0});", "gsap.set('#mlist .mi',{autoAlpha:0});",
          f"tl.fromTo('#mlist',{{autoAlpha:0,y:40,rotation:-3}},{{autoAlpha:1,y:0,rotation:-3,duration:.5,ease:'back.out(1.5)',immediateRender:false}},{a - .2:.3f});"]
    for i, (iid, _, t) in enumerate(items):
        tw.append(f"tl.fromTo('#{iid}',{{autoAlpha:0,x:24}},{{autoAlpha:1,x:0,duration:.3,ease:'power2.out',immediateRender:false}},{t - .05:.3f});")
        if i in (1, 3):   # ticked as she names them
            tw.append(f"tl.to('#{iid} .box',{{backgroundColor:'{YEL}',duration:.15}},{t + .35:.3f});")
            tw.append(f"tl.fromTo('#{iid} path',{{strokeDashoffset:1}},{{strokeDashoffset:0,duration:.25,ease:'power2.out',immediateRender:false}},{t + .35:.3f});")
    tw += [f"tl.to('#mlist',{{autoAlpha:0,y:-20,duration:.18}},{b - .18:.3f});", f"tl.set('#mlist',{{autoAlpha:0}},{b:.3f});"]
    return html, tw, (l1 + .35, mg + .35)


def ladder():
    """'I start with big dreams and then I work backward': a ladder drawn from the dream back down to today"""
    a = kw('backward', T['planner2'], END['planner2']) - .3
    b = END['planner2']
    nodes = ['big dream', 'RM / bulan', 'first product', 'minggu ni']
    rows = ''.join(f'<div class="ln" id="ln{k}"><span class="dot"></span><span>{lab}</span></div>' for k, lab in enumerate(nodes))
    html = [f'<div id="ladder" class="ladder"><div class="rail"><div class="fill" id="lfill"></div></div>{rows}</div>']
    tw = ["gsap.set('#ladder',{autoAlpha:0});", "gsap.set('#ladder .ln',{autoAlpha:0});", "gsap.set('#lfill',{scaleY:0});",
          f"tl.fromTo('#ladder',{{autoAlpha:0,y:30}},{{autoAlpha:1,y:0,duration:.4,ease:'power2.out',immediateRender:false}},{a:.3f});",
          f"tl.to('#lfill',{{scaleY:1,duration:1.6,ease:'power1.inOut'}},{a + .2:.3f});"]
    for k in range(len(nodes)):
        tw.append(f"tl.fromTo('#ln{k}',{{autoAlpha:0,x:20}},{{autoAlpha:1,x:0,duration:.3,ease:'power2.out',immediateRender:false}},{a + .2 + k * .5:.3f});")
    tw += [f"tl.to('#ladder',{{autoAlpha:0,duration:.16}},{b - .16:.3f});", f"tl.set('#ladder',{{autoAlpha:0}},{b:.3f});"]
    return html, tw


def cutouts():
    html = []
    for k, (n, (a, b)) in enumerate(CUT_SPAN.items()):
        st = SEG[CUTOUT[n][0]]['frame'] / 30
        d = (SEG[CUTOUT[n][1]]['frame'] + SEG[CUTOUT[n][1]]['frames']) / 30 - st
        html.append(f'<video id="cut_{n}" class="full g cutv" src="cut/{n}/assets/subject.webm" muted playsinline data-start="{st:.3f}" '
                    f'data-media-start="0" data-duration="{d:.3f}" data-track-index="{30 + k}"></video>')
    return html


GIRL_F = 'sepia(.14) saturate(.88) contrast(.94) brightness(1.05) hue-rotate(-4deg)'


def grades():
    tw = [f"gsap.set('.g',{{filter:'{GIRL_F}'}});"]
    for t in CUTS:
        tw.append(f"tl.fromTo('#stage',{{scale:1.04}},{{scale:1,duration:.3,ease:'power2.out',immediateRender:false}},{t:.3f});")
    return tw


def sfx_list(orbit_pops, ticks):
    S = [('sparkle', kw('9', T['hook'], END['hook']) + .1, .22), ('whoosh-short', kw('quit', T['hook'], END['hook']) - .05, .2),
         ('whoosh-short', kw('plan', T['plan'], END['plan']) - .1, .25), ('sparkle', kw('terbalik', T['plan'], END['plan']), .2),
         ('whoosh-short', kw('First', T['first'], END['first']) - .1, .2), ('whoosh-short', T['second'], .2),
         ('whoosh-short', kw('third', T['third'], END['third2']) - .1, .2),
         ('pop', kw('RM20', T['example'], END['example']) - .3, .2), ('click-soft', kw('reduce', T['example'], END['example']), .5),
         ('pop', kw('RM5', T['example'], END['example']) - .15, .2),
         ('sparkle', kw('power', T['planner'], END['planner']), .2), ('whoosh-short', kw('backward', T['planner2'], END['planner2']) - .3, .2),
         ('sparkle', kw('dreams', T['cta'], END['cta']), .22)]
    S += [('pop', t - .05, .14) for t in orbit_pops]
    S += [('click', t, .45) for t in ticks]
    return S


SFX_LEN = {'whoosh-short': .57, 'pop': .72, 'sparkle': 1.8, 'click': .3, 'click-soft': .37}
SFX_GAIN = 0.75


def audio(S):
    out, lanes = [], []
    for k, (name, t, vol) in enumerate(sorted(S, key=lambda x: x[1])):
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
#stage{{position:absolute;inset:0;transform-origin:45% 40%}}
.full{{position:absolute;inset:0;width:100%;height:100%;object-fit:cover}}
#bgv{{z-index:0}}
.punch.back{{z-index:3}}
.cutv{{z-index:4}}
.fx{{position:absolute;inset:0;pointer-events:none}}
#gwarm{{z-index:7;background:linear-gradient(180deg,rgba(255,226,200,.10),rgba(255,196,170,.14));mix-blend-mode:soft-light}}
#gvig{{z-index:7;background:radial-gradient(120% 70% at 45% 42%,rgba(255,255,255,0) 52%,rgba(60,35,25,.34) 100%)}}
#ggrad{{z-index:7;background:linear-gradient(180deg,rgba(60,35,25,.34) 0%,rgba(60,35,25,0) 24%,rgba(60,35,25,0) 60%,rgba(40,24,18,.55) 100%)}}

/* captions: calm lowercase, chest band, bottom edge at y=1450 */
.cap{{position:absolute;left:60px;right:110px;bottom:{CAP_BOTTOM}px;z-index:8;text-align:center;color:{CREAM};
  font:500 54px Inter;letter-spacing:-.8px;line-height:1.18;text-shadow:0 2px 22px rgba(40,20,12,.75),0 1px 4px rgba(40,20,12,.5)}}
.gw{{display:inline-block}}
.gw.hl{{color:{YEL};font:italic 400 66px 'Instrument Serif';letter-spacing:0;line-height:1}}

/* punch words */
.punch{{position:absolute;left:0;right:0;z-index:8;text-align:center;color:{YEL};font-family:'Instrument Serif';font-style:italic;
  font-weight:400;line-height:1.05;white-space:nowrap;text-shadow:0 8px 34px rgba(60,30,20,.45)}}
.punch .mk{{display:inline-block;overflow:hidden;padding:0 .03em .12em;margin-bottom:-.12em;vertical-align:bottom}}
.punch .ch{{display:inline-block}}
.spark{{position:absolute;z-index:8;color:{YEL};line-height:1;text-shadow:0 0 18px rgba(250,230,122,.5)}}
.ink{{position:absolute;z-index:9;overflow:visible;filter:drop-shadow(0 4px 14px rgba(60,30,20,.45))}}
.note{{position:absolute;z-index:9;color:{CREAM};font:600 54px Caveat;line-height:1;text-align:center;text-shadow:0 2px 16px rgba(40,20,12,.7)}}

/* step chips */
.chip{{position:absolute;left:50px;top:236px;z-index:9;display:flex;align-items:center;gap:16px;padding:10px 26px 10px 10px;border-radius:99px;
  background:rgba(255,248,239,.94);box-shadow:0 14px 40px rgba(40,20,12,.35)}}
.chip .n{{width:64px;height:64px;border-radius:50%;background:{YEL};color:#2b1d16;font:italic 400 40px 'Instrument Serif';display:flex;
  align-items:center;justify-content:center}}
.chip .l{{color:#2b1d16;font:600 34px Inter;letter-spacing:-.6px}}

/* money card */
.mcard{{position:absolute;left:735px;top:520px;width:300px;z-index:9;padding:22px 24px 20px;border-radius:30px;background:rgba(255,248,239,.95);
  box-shadow:0 26px 60px rgba(40,20,12,.45);color:#2b1d16;text-align:left}}
.mcard .lbl,.mlist .lbl{{font:600 21px Inter;letter-spacing:.14em;text-transform:uppercase;color:#9a7b62;margin-bottom:10px}}
.mcard .row{{position:relative;height:66px}}
.mcard .nums{{font:italic 400 64px 'Instrument Serif';line-height:1;white-space:nowrap}}
.mcard .nums.y{{color:#c9971c}}
#mstrike{{position:absolute;left:-4px;right:-4px;top:26px;height:12px;width:calc(100% + 8px);overflow:visible}}
.mcard .per{{font:500 26px Inter;color:#6b5444;margin-top:2px}}

/* orbit tiles */
.orb{{position:absolute;left:0;top:0;width:{TW_}px;height:{TH_}px}}
.orb.b{{z-index:3;filter:brightness(.8)}}
.orb.f{{z-index:6}}
.pop{{width:100%;height:100%}}
.itile{{width:100%;height:100%;border-radius:26px;background:rgba(255,248,239,.96);border:4px solid {YEL};display:flex;flex-direction:column;
  align-items:center;justify-content:center;box-shadow:0 20px 50px rgba(40,20,12,.45)}}
.itile .ib{{font:italic 400 52px 'Instrument Serif';color:#2b1d16;line-height:1}}
.itile .is{{font:600 22px Inter;letter-spacing:.12em;text-transform:uppercase;color:#9a7b62;margin-top:4px}}

/* milestones */
.mlist{{position:absolute;left:705px;top:500px;width:330px;z-index:9;padding:22px 22px 14px;border-radius:30px;background:rgba(255,248,239,.95);
  box-shadow:0 26px 60px rgba(40,20,12,.45);color:#2b1d16}}
.mi{{display:flex;align-items:center;gap:12px;font:600 27px Inter;letter-spacing:-.4px;margin-bottom:12px;white-space:nowrap}}
.mi .box{{width:38px;height:38px;flex:none;border-radius:10px;border:3px solid #2b1d16;display:flex;align-items:center;justify-content:center}}
.mi .box svg{{width:28px;height:28px;overflow:visible}}

/* ladder */
.ladder{{position:absolute;left:740px;top:470px;width:300px;height:520px;z-index:9;padding:26px 20px 26px 74px;border-radius:30px;
  background:rgba(255,248,239,.95);box-shadow:0 26px 60px rgba(40,20,12,.45);display:flex;flex-direction:column;justify-content:space-between}}
.ladder .rail{{position:absolute;left:40px;top:44px;bottom:44px;width:6px;border-radius:3px;background:rgba(43,29,22,.15)}}
.ladder .fill{{position:absolute;inset:0;border-radius:3px;background:{YEL};transform-origin:50% 0%}}
.ln{{position:relative;font:600 29px Inter;color:#2b1d16;letter-spacing:-.4px;white-space:nowrap}}
.ln .dot{{position:absolute;left:-46px;top:6px;width:24px;height:24px;border-radius:50%;background:{YEL};border:4px solid #2b1d16}}
'''

SAFE_GUIDE = ('<div style="position:absolute;inset:0;z-index:99;pointer-events:none">'
              '<div style="position:absolute;left:0;right:0;top:0;height:220px;background:rgba(255,0,0,.28)"></div>'
              '<div style="position:absolute;left:0;right:0;top:1470px;bottom:0;background:rgba(255,0,0,.28)"></div>'
              '<div style="position:absolute;left:0;width:35px;top:220px;height:1250px;background:rgba(255,0,0,.28)"></div>'
              '<div style="position:absolute;right:0;width:35px;top:220px;height:935px;background:rgba(255,0,0,.28)"></div>'
              '<div style="position:absolute;right:0;width:100px;top:1155px;height:315px;background:rgba(255,0,0,.28)"></div></div>')


def build():
    c_html, c_tw = captions()
    p_back, p_front, p_tw = punches()
    for i, h in enumerate(p_back):
        p_back[i] = h.replace('class="punch"', 'class="punch back"')
    sp_html, sp_tw = sparkles()
    st_html, st_tw = strike_95()
    rn_html, rn_tw = reverse_note()
    ch_html, ch_tw = step_chips()
    m_html, m_tw = money_card()
    o_html, o_tw, pops = orbit()
    ml_html, ml_tw, ticks = milestones()
    ld_html, ld_tw = ladder()
    tweens = grades() + p_tw + o_tw + c_tw + sp_tw + st_tw + rn_tw + ch_tw + m_tw + ml_tw + ld_tw
    nl = '\n'
    return f'''<!doctype html>
<html lang="en" data-resolution="portrait">
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
{nl.join(audio(sfx_list(pops, ticks)))}
  <div id="stage">
    <video id="bgv" class="full g" src="assets/aroll.mp4" muted playsinline data-start="0" data-media-start="0" data-duration="{DUR:.3f}" data-track-index="0"></video>
{nl.join(p_back)}
{nl.join(cutouts())}
{nl.join(o_html)}
  </div>
  <div id="gwarm" class="fx"></div><div id="gvig" class="fx"></div><div id="ggrad" class="fx"></div>
{nl.join(p_front)}
{nl.join(sp_html)}
{nl.join(st_html)}
{nl.join(rn_html)}
{nl.join(ch_html)}
{nl.join(m_html)}
{nl.join(ml_html)}
{nl.join(ld_html)}
{nl.join(c_html)}
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


with open('index.html', 'w', encoding='utf-8', newline='\n') as _f:
    _f.write(build())
print(f'wrote index.html {DUR:.3f}s  {len(PHRASES)} caption phrases  cuts {len(CUTS)}')
