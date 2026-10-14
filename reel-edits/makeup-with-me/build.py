#!/usr/bin/env python3
"""makeup with me (power planner ramble): cool girl look all the way through, captions on every line, one motion
graphic per section. Built from the /video-edit template: same machinery (cut times from segments.json, cutout layer,
grades, SFX lanes, SAFE_GUIDE), new content.

PY build.py            writes index.html
PY build.py --safe     same + red Instagram safe-zone guide (snapshots only, never render with it)
"""
import json
import math
import re
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
    SEGS = json.load(_f)
SEG = {s['id']: s for s in SEGS}
# cut times = exact first frame of each segment, nudged 2ms early so a tl.set lands ON that frame
T = {k: s['frame'] / 30 - .002 if s['frame'] else 0.0 for k, s in SEG.items()}
CUTS = [T[s['id']] for s in SEGS[1:]]
with open('words_cut.json', encoding='utf-8') as _f:
    WORDS = json.load(_f)

GIRL_F = 'sepia(.18) saturate(.9) contrast(.93) brightness(1.05) hue-rotate(-5deg)'
C = 'left:0;right:0;text-align:center;'
TW, TO = [], []          # timeline tweens / one-time gsap.set lines
HTML_BACK, HTML_FRONT = [], []   # behind the cutout / above it


def show(sel, a, b, enter="{autoAlpha:0,y:24,scale:.94}", to="{autoAlpha:1,y:0,scale:1,duration:.4,ease:'power3.out'}",
         exit_="{autoAlpha:0,y:-12,filter:'blur(8px)',duration:.16,ease:'power2.in'}"):
    """element hidden until a, eased in, eased out and hard-killed at b"""
    TO.append(f"gsap.set('{sel}',{{autoAlpha:0}});")
    to = to[:-1] + ",immediateRender:false}"
    TW.append(f"tl.fromTo('{sel}',{enter},{to},{a:.3f});")
    if b < DUR - .01:
        TW.append(f"tl.to('{sel}',{exit_},{b - .16:.3f});")
        TW.append(f"tl.set('{sel}',{{autoAlpha:0}},{b:.3f});")


def sparks(prefix, pts, t, end):
    for k, (x, y, sz) in enumerate(pts):
        sid = f'{prefix}{k}'
        HTML_FRONT.append(f'<div id="{sid}" class="spark" style="left:{x}px;top:{y}px;font-size:{sz}px">&#10022;</div>')
        TO.append(f"gsap.set('#{sid}',{{autoAlpha:0,scale:0}});")
        tk = t + k * .12
        TW.extend([f"tl.to('#{sid}',{{autoAlpha:1,scale:1,rotation:90,duration:.35,ease:'back.out(2.5)'}},{tk:.3f});",
               f"tl.to('#{sid}',{{scale:.6,duration:.45,yoyo:true,repeat:{max(0, min(3, int((end - tk - .7) / .45)))},ease:'sine.inOut'}},{tk + .35:.3f});",
               f"tl.to('#{sid}',{{autoAlpha:0,scale:0,duration:.14}},{end - .14:.3f});",
               f"tl.set('#{sid}',{{autoAlpha:0}},{end:.3f});"])


# ------------------------------------------------------------------ captions (every line, word by word)
PUNCH = {'makeup', 'ramble', 'together', 'perfect', 'business', 'excel', 'fail', 'power', 'planner', 'balance',
         'career', 'own', 'eight', 'achieved', 'rambling', 'bye'}
FIX = {'Okay': 'okay'}


def chunks():
    out = []
    for seg in WORDS:
        ws = [(t, w) for t, w in seg['words']]
        if seg['id'] == 'hook':
            ws = [(0.02, 'Okay,')] + ws
        end = SEG[seg['id']]['frame'] / 30 + SEG[seg['id']]['frames'] / 30
        cur = []
        for i, (t, w) in enumerate(ws):
            cur.append((t, w))
            nxt = ws[i + 1][0] if i + 1 < len(ws) else None
            brk = w[-1] in '.,?!' and len(cur) >= 2 or len(cur) >= 4 or (nxt is not None and nxt - t > 1.0 and len(cur) >= 2)
            if brk or nxt is None:
                out.append((cur, end))
                cur = []
    # each chunk shows until the next chunk starts (or its segment ends)
    res = []
    for k, (cw, end) in enumerate(out):
        a = cw[0][0] - .06
        b = min(out[k + 1][0][0][0] - .06, end) if k + 1 < len(out) else DUR
        b = max(b, a + .3)
        res.append((a, b, cw))
    return res


def captions():
    for k, (a, b, cw) in enumerate(chunks()):
        spans = []
        for j, (t, w) in enumerate(cw):
            clean = w.strip('.,?!').lower()
            txt = w.lower().rstrip(',').replace("'", '&#8217;')
            cls = 'cw p' if clean in PUNCH else 'cw'
            wid = f'cap{k}-{j}'
            spans.append(f'<span id="{wid}" class="{cls}">{txt}</span>')
            TO.append(f"gsap.set('#{wid}',{{autoAlpha:0}});")
            dy = 26 if clean in PUNCH else 14
            TW.append(f"tl.fromTo('#{wid}',{{autoAlpha:0,y:{dy}}},{{autoAlpha:1,y:0,duration:.26,ease:'power2.out',"
                      f"immediateRender:false}},{max(a, t - .05):.3f});")
        HTML_FRONT.append(f'<div id="cap{k}" class="cap">{" ".join(spans)}</div>')
        if b < DUR - .01:
            TW.append(f"tl.to('#cap{k}',{{autoAlpha:0,duration:.08}},{b - .08:.3f});")
            TW.append(f"tl.set('#cap{k}',{{autoAlpha:0}},{b:.3f});")


# ------------------------------------------------------------------ motion graphics, one per section
def g_hook():
    a, b = .9, T['perfect']
    HTML_BACK.append(f'<div id="ttl" class="ser y" style="{C}top:228px;font-size:150px">makeup with me</div>')
    show('#ttl', 1.12, b, enter="{autoAlpha:0,y:40,filter:'blur(14px)'}", to="{autoAlpha:1,y:0,filter:'blur(0px)',duration:.6,ease:'expo.out'}")
    HTML_FRONT.append('<div id="note1" class="note" style="left:46px;top:470px;transform:rotate(-6deg)">sambil ramble<br>in the car</div>'
                      '<svg id="arr1" class="arr" style="left:150px;top:600px" width="200" height="150" viewBox="0 0 200 150">'
                      '<path d="M20 10 C 30 90, 90 130, 175 120" /><path d="M150 100 L178 121 L150 140" /></svg>')
    show('#note1', 2.24, b)
    TO.append("gsap.set('#arr1 path',{strokeDasharray:300,strokeDashoffset:300});")
    show('#arr1', 2.5, b, enter="{autoAlpha:0}", to="{autoAlpha:1,duration:.1}")
    TW.append("tl.to('#arr1 path',{strokeDashoffset:0,duration:.55,ease:'power2.out',stagger:.25,immediateRender:false},2.5);")
    sparks('sh', [(110, 250, 54), (930, 300, 40), (880, 430, 28)], 1.3, b)


def g_perfect():
    b = T['notperf']
    for pid, txt, t, st, rot in (('pl1', 'life together', 10.6, 'left:46px;top:330px', -5),
                                 ('pl2', 'perfect', 13.1, 'right:60px;top:430px', 4)):
        HTML_FRONT.append(f'<div id="{pid}" class="pill" style="{st};transform:rotate({rot}deg)"><span class="tick">&#10003;</span>{txt}</div>')
        show(f'#{pid}', t, b, enter="{autoAlpha:0,scale:.3,y:40}", to="{autoAlpha:1,scale:1,y:0,duration:.45,ease:'back.out(1.8)'}")


def g_notperf():
    a, b = 14.25, T['together']
    HTML_FRONT.append(f'<div id="perf" class="ser" style="{C}top:262px;font-size:200px;color:{CREAM}">perfect.</div>'
                      '<svg id="strike" class="arr" style="left:250px;top:330px" width="580" height="120" viewBox="0 0 580 120">'
                      '<path d="M10 70 C 120 40, 220 95, 320 55 S 500 40, 570 62" style="stroke-width:16" /></svg>'
                      f'<div id="notw" class="note y" style="left:150px;top:224px;font-size:82px;transform:rotate(-10deg)">not</div>')
    show('#perf', a, b)
    TO.append("gsap.set('#strike path',{strokeDasharray:700,strokeDashoffset:700});")
    show('#strike', 14.95, b, enter="{autoAlpha:0}", to="{autoAlpha:1,duration:.05}")
    TW.append("tl.to('#strike path',{strokeDashoffset:0,duration:.35,ease:'power3.out',immediateRender:false},14.95);")
    show('#notw', 14.92, b, enter="{autoAlpha:0,scale:1.6,rotation:-25}", to="{autoAlpha:1,scale:1,rotation:-10,duration:.35,ease:'back.out(2)'}")


def g_together():
    a, b = 16.25, T['honest']
    HTML_FRONT.append('<div id="load" class="card" style="left:200px;top:236px;width:680px">'
                      '<div class="note" style="position:static;font-size:50px;text-align:left">my life, put together</div>'
                      '<div class="bar"><div id="fill" class="fill"></div></div>'
                      '<div id="still" class="note y" style="position:static;font-size:40px;text-align:right;margin-top:6px">still loading...</div></div>')
    show('#load', a, b)
    TO.extend(["gsap.set('#fill',{width:'0%'});", "gsap.set('#still',{autoAlpha:0});"])
    TW.extend(["tl.to('#fill',{width:'38%',duration:1.0,ease:'power2.out'},17.4);",
           "tl.to('#fill',{width:'63%',duration:.8,ease:'power2.out'},18.5);",
           "tl.to('#fill',{width:'91%',duration:1.2,ease:'power2.out'},19.6);",
           "tl.to('#fill',{width:'84%',duration:.4,ease:'power2.inOut'},20.9);",
           "tl.to('#still',{autoAlpha:1,duration:.25},21.0);",
           "tl.fromTo('#load',{x:0},{x:9,duration:.06,yoyo:true,repeat:5,ease:'none',immediateRender:false},21.97);"])


def g_honest():
    a, b = 24.5, T['excel']
    bars = ''.join(f'<div class="b8" id="b8{i}"></div>' for i in range(8))
    HTML_FRONT.append(f'<div id="bars" style="position:absolute;left:0;right:0;top:236px;height:200px;display:flex;justify-content:center;'
                      f'align-items:flex-end;gap:24px;z-index:8">{bars}</div>'
                      f'<div id="bizl" class="note y" style="{C}top:445px;font-size:58px">business</div>')
    TO.append("gsap.set('#bars',{autoAlpha:0});")
    TW.append(f"tl.set('#bars',{{autoAlpha:1}},{a:.3f});")
    TO.append("gsap.set('.b8',{height:0});")
    TW.append("tl.to('.b8',{height:46,duration:.35,ease:'back.out(2)',stagger:.06,immediateRender:false},%.3f);" % a)
    TW.append("tl.to('#b83',{height:200,backgroundColor:'%s',duration:.6,ease:'expo.out'},26.0);" % YEL)
    TW.append("tl.to(['#b80','#b81','#b82','#b84','#b85','#b86','#b87'],{height:18,opacity:.45,duration:.5,ease:'power2.out'},27.3);")
    TW.extend([f"tl.to('#bars',{{autoAlpha:0,duration:.16}},{b - .16:.3f});", f"tl.set('#bars',{{autoAlpha:0}},{b:.3f});"])
    show('#bizl', 29.98, b, enter="{autoAlpha:0,scale:.5}", to="{autoAlpha:1,scale:1,duration:.35,ease:'back.out(2)'}")


def g_excel():
    b = T['why']
    HTML_FRONT.append('<div id="exw" class="ser y" style="left:80px;top:236px;font-size:170px">excel<span class="arrw">&#8599;</span></div>'
                      f'<div id="faw" class="ser" style="right:90px;top:236px;font-size:170px;color:{CREAM}">fail<span class="arrw">&#8600;</span></div>')
    show('#exw', 31.92, b, enter="{autoAlpha:0,y:60,filter:'blur(12px)'}", to="{autoAlpha:1,y:0,filter:'blur(0px)',duration:.5,ease:'expo.out'}")
    show('#faw', 34.3, b, enter="{autoAlpha:0,y:-50,filter:'blur(12px)'}", to="{autoAlpha:1,y:0,filter:'blur(0px)',duration:.5,ease:'expo.out'}")
    TW.append("tl.to('#faw',{y:26,rotation:4,duration:.6,ease:'bounce.out'},34.9);")


def g_why():
    b = T['notonly']
    HTML_FRONT.append(f'<div id="pp" class="ser y" style="{C}top:236px;font-size:160px">power planner</div>')
    show('#pp', 37.7, 40.1, enter="{autoAlpha:0,scale:1.15,filter:'blur(14px)'}", to="{autoAlpha:1,scale:1,filter:'blur(0px)',duration:.5,ease:'expo.out'}")
    # balance scale: beam tilts, then levels out on "balance my life"
    HTML_FRONT.append('<div id="scale" style="position:absolute;left:340px;top:236px;width:400px;height:240px;z-index:8">'
                      '<svg width="400" height="240" viewBox="0 0 400 240" class="scl">'
                      '<path d="M200 40 L200 210 M140 214 L260 214" />'
                      '<g id="beam"><path d="M60 50 L340 50" /><circle cx="200" cy="44" r="10" class="dot"/>'
                      '<g id="panL"><path d="M60 50 L30 120 M60 50 L90 120 M22 120 Q60 150 98 120 Z" /></g>'
                      '<g id="panR"><path d="M340 50 L310 120 M340 50 L370 120 M302 120 Q340 150 378 120 Z" /></g></g></svg></div>'
                      f'<div id="bal" class="note" style="{C}top:470px;font-size:56px">balance my life</div>')
    show('#scale', 40.15, b)
    TO.extend(["gsap.set('#beam',{rotation:-16,svgOrigin:'200 44'});",
           "gsap.set('#panL',{rotation:16,svgOrigin:'60 50'});", "gsap.set('#panR',{rotation:16,svgOrigin:'340 50'});"])
    TW.extend(["tl.to('#beam',{rotation:0,duration:1.1,ease:'elastic.out(1,.45)'},40.6);",
           "tl.to(['#panL','#panR'],{rotation:0,duration:1.1,ease:'elastic.out(1,.45)'},40.6);"])
    show('#bal', 40.4, b)
    sparks('sb', [(250, 300, 36), (790, 270, 44)], 40.7, b)


def g_notonly():
    b = T['own']
    HTML_FRONT.append(f'<div id="nol" class="note" style="{C}top:226px;font-size:60px">not only...</div>')
    show('#nol', 42.0, b)
    for k, (txt, t, x, y) in enumerate((('business', 42.9, 140, 318), ('finance', 44.84, 600, 318),
                                       ('professional', 46.4, 110, 412), ('career', 47.88, 640, 412))):
        HTML_FRONT.append(f'<div id="ch{k}" class="pill" style="left:{x}px;top:{y}px"><span class="dotc"></span>{txt}</div>')
        show(f'#ch{k}', t, b, enter="{autoAlpha:0,scale:.3,y:30}", to="{autoAlpha:1,scale:1,y:0,duration:.42,ease:'back.out(1.9)'}")


def g_own():
    b = T['eight']
    HTML_FRONT.append('<div id="nw" class="note" style="left:60px;top:250px;font-size:54px;transform:rotate(-5deg)">'
                      'other planners<br><span class="y">not working</span> <span class="xx">&#10007;</span></div>')
    show('#nw', 52.7, 54.5)
    # spinning sticker on "that's why I create my own"
    HTML_FRONT.append('<div id="stk" style="position:absolute;left:378px;top:230px;width:330px;height:330px;z-index:8">'
                      '<svg width="330" height="330" viewBox="0 0 330 330"><defs><path id="circ" d="M165 165 m-122 0 a122 122 0 1 1 244 0 a122 122 0 1 1 -244 0"/></defs>'
                      f'<circle cx="165" cy="165" r="158" fill="{YEL}"/>'
                      '<g id="ring"><text class="stxt"><textPath href="#circ">MADE BY ME &#10022; MY OWN PLANNER &#10022; </textPath></text></g></svg>'
                      '<div class="stc">my<br>own</div></div>')
    show('#stk', 54.55, b, enter="{autoAlpha:0,scale:.2,rotation:-90}", to="{autoAlpha:1,scale:1,rotation:0,duration:.55,ease:'back.out(1.6)'}")
    TW.append(f"tl.fromTo('#ring',{{rotation:0}},{{rotation:120,svgOrigin:'165 165',duration:{b - 54.55:.3f},ease:'none',immediateRender:false}},54.55);")


# 8 category pills orbit her on "the eight category of life" (front copy above the cutout, back copy below it)
CATS = ['personal', 'home', 'finance', 'spiritual', 'fun', 'environment', 'relationship', 'health']
CX, CY, RX, RY = 540, 545, 430, 72
O_IN, REV, STEP = 57.2, 7.5, 0.1


def g_eight():
    o_out = T['belt']
    HTML_FRONT.append(f'<div id="e8" class="ser y" style="{C}top:226px;font-size:132px">8 <span style="color:{CREAM}">categories</span></div>'
                      )
    show('#e8', 57.02, o_out, enter="{autoAlpha:0,y:40,filter:'blur(12px)'}", to="{autoAlpha:1,y:0,filter:'blur(0px)',duration:.5,ease:'expo.out'}")
    n = len(CATS)
    for i, cat in enumerate(CATS):
        frames, t = [], O_IN
        while t <= o_out + 1e-6:
            th = 2 * math.pi * ((t - O_IN) / REV) + i * 2 * math.pi / n
            s = math.sin(th)
            frames.append((t, CX + RX * math.cos(th), CY + RY * s, .72 + .28 * (s + 1) / 2, s))
            t = round(t + STEP, 4)
        for side in ('b', 'f'):
            oid = f'o{side}{i}'
            html = f'<div id="{oid}" class="orb {side}"><div class="pop"><div class="opill">{cat}</div></div></div>'
            (HTML_BACK if side == 'b' else HTML_FRONT).append(html)
            vis = (lambda s: 1 if s > 0 else 0) if side == 'f' else (lambda s: 0 if s > 0 else 1)
            t0, x0, y0, sc0, s0 = frames[0]
            TO.append(f"gsap.set('#{oid}',{{xPercent:-50,yPercent:-50,x:{x0:.1f},y:{y0:.1f},scale:{sc0:.3f},autoAlpha:0}});")
            TW.append(f"tl.set('#{oid}',{{autoAlpha:{vis(s0)}}},{t0:.3f});")
            kf = ','.join(f"{{x:{x:.1f},y:{y:.1f},scale:{sc:.3f},autoAlpha:{vis(s)},duration:{STEP},ease:'none'}}"
                          for _, x, y, sc, s in frames[1:])
            TW.append(f"tl.to('#{oid}',{{keyframes:[{kf}]}},{t0:.3f});")
            TW.append(f"tl.set('#{oid}',{{autoAlpha:0}},{o_out:.3f});")
            TO.append(f"gsap.set('#{oid} .pop',{{scale:0}});")
            TW.append(f"tl.to('#{oid} .pop',{{scale:1,duration:.4,ease:'back.out(1.8)'}},{O_IN + i * .09:.3f});")
            TW.append(f"tl.to('#{oid} .pop',{{scale:0,duration:.18,ease:'power2.in'}},{o_out - .22:.3f});")


def g_belt():
    b = T['outro']
    circ = ''.join(f'<svg id="tk{i}" class="tk" width="96" height="96" viewBox="0 0 96 96"><circle cx="48" cy="48" r="42"/>'
                   f'<path d="M28 50 L43 64 L69 34"/></svg>' for i in range(3))
    HTML_FRONT.append(f'<div id="tks" style="position:absolute;left:0;right:0;top:240px;display:flex;justify-content:center;gap:34px;z-index:8">{circ}</div>'
                      f'<div id="gal" class="note y" style="{C}top:356px;font-size:64px">goals achieved &#10022;</div>')
    TO.append("gsap.set('#tks',{autoAlpha:0});")
    TW.append("tl.set('#tks',{autoAlpha:1},66.3);")
    for i, t in enumerate((66.38, 66.62, 66.98)):
        TO.extend([f"gsap.set('#tk{i}',{{scale:0}});", f"gsap.set('#tk{i} path',{{strokeDasharray:80,strokeDashoffset:80}});"])
        TW.extend([f"tl.to('#tk{i}',{{scale:1,duration:.3,ease:'back.out(2.4)'}},{t:.3f});",
               f"tl.to('#tk{i} path',{{strokeDashoffset:0,duration:.25,ease:'power2.out'}},{t + .12:.3f});"])
    TW.extend([f"tl.to('#tks',{{autoAlpha:0,duration:.16}},{b - .16:.3f});", f"tl.set('#tks',{{autoAlpha:0}},{b:.3f});"])
    show('#gal', 67.0, b)


def g_outro():
    HTML_FRONT.append(f'<div id="ty" class="ser y" style="{C}top:232px;font-size:190px">thank you</div>'
                      f'<div id="ty2" class="note" style="{C}top:420px;font-size:58px">for rambling with me</div>')
    show('#ty', 72.1, T['bye'])
    show('#ty2', 73.45, T['bye'], to="{autoAlpha:1,y:0,scale:1,duration:.3,ease:'power3.out'}")
    sparks('so', [(150, 260, 50), (900, 300, 42), (210, 470, 30), (850, 520, 34)], 72.2, DUR)


def grades():
    tw = [f"gsap.set('.g',{{filter:'{GIRL_F}'}});"]
    for t in CUTS:
        tw.append(f"tl.fromTo('#stage',{{scale:1.05}},{{scale:1,duration:.32,ease:'power2.out',immediateRender:false}},{t:.3f});")
    return tw


SFX = [('sparkle', 1.1, .2), ('whoosh-short', 2.4, .18), ('pop', 10.6, .16), ('pop', 13.1, .16),
       ('whoosh-short', 14.9, .25), ('whoosh-short', 16.2, .2), ('click-soft', 21.97, .5),
       ('pop', 24.5, .14), ('whoosh-short', 26.0, .2), ('whoosh-short', 31.9, .22), ('whoosh-short', 34.3, .2),
       ('sparkle', 37.7, .18), ('click-soft', 40.6, .45), ('pop', 42.9, .15), ('pop', 44.84, .15), ('pop', 46.4, .15),
       ('pop', 47.88, .15), ('whoosh-short', 54.55, .24), ('sparkle', 57.0, .2), ('whoosh-short', 57.2, .18),
       ('click', 66.38, .45), ('click', 66.62, .45), ('click', 66.98, .45), ('sparkle', 72.1, .2), ('pop', 74.0, .2)]
SFX_LEN = {'whoosh-short': .57, 'pop': .72, 'sparkle': 1.8, 'click': .3, 'click-soft': .37}
SFX_GAIN = 0.75   # sounds sit 25% under the original levels: subtle, never louder than the voice


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
#ggrad{{z-index:7;background:linear-gradient(180deg,rgba(60,35,25,.34) 0%,rgba(60,35,25,0) 30%,rgba(60,35,25,0) 58%,rgba(40,24,18,.55) 100%)}}

.ser{{position:absolute;z-index:8;font-family:'Instrument Serif';font-style:italic;font-weight:400;line-height:.95;white-space:nowrap;
  letter-spacing:-.01em;text-shadow:0 4px 30px rgba(60,30,20,.55)}}
.y{{color:{YEL}}}
.back{{z-index:3}}
#ttl{{z-index:3}}
.note{{position:absolute;z-index:8;font:600 54px Caveat;color:{CREAM};line-height:1.0;text-shadow:0 2px 18px rgba(60,30,20,.6)}}
.arr{{position:absolute;z-index:8;overflow:visible}}
.arr path{{fill:none;stroke:{YEL};stroke-width:7;stroke-linecap:round;stroke-linejoin:round}}
.spark{{position:absolute;z-index:8;color:{YEL};line-height:1;text-shadow:0 0 18px rgba(250,230,122,.5)}}
.arrw{{font-family:Inter;font-style:normal;font-weight:500;font-size:.5em;margin-left:.08em;vertical-align:.45em}}

.cap{{position:absolute;left:60px;right:60px;top:1268px;z-index:9;text-align:center;color:{CREAM};font:500 58px Inter;letter-spacing:-1px;
  line-height:1.18;text-shadow:0 2px 22px rgba(50,25,15,.75),0 1px 4px rgba(50,25,15,.5)}}
.cw{{display:inline-block}}
.cw.p{{font:italic 400 84px 'Instrument Serif';letter-spacing:0;color:{YEL};line-height:.9}}

.pill{{position:absolute;z-index:8;padding:14px 26px 14px 18px;border-radius:99px;background:rgba(255,248,239,.95);color:#3a2620;
  font:600 38px Inter;letter-spacing:-.5px;white-space:nowrap;box-shadow:0 18px 40px rgba(50,25,15,.35)}}
.tick{{display:inline-block;width:46px;height:46px;line-height:46px;margin-right:12px;border-radius:50%;background:{YEL};color:#3a2620;
  text-align:center;font-size:30px;vertical-align:2px}}
.dotc{{display:inline-block;width:18px;height:18px;border-radius:50%;background:{YEL};margin:0 14px 4px 8px;box-shadow:0 0 0 3px rgba(58,38,32,.25)}}
.card{{position:absolute;z-index:8;padding:22px 30px 18px;border-radius:30px;background:rgba(58,36,28,.55);
  border:2px solid rgba(255,248,239,.35);box-shadow:0 20px 50px rgba(40,20,10,.3)}}
.bar{{margin-top:14px;height:30px;border-radius:99px;border:3px solid {CREAM};padding:3px}}
.fill{{height:100%;border-radius:99px;background:{YEL}}}
.b8{{width:52px;border-radius:14px;background:{CREAM};box-shadow:0 10px 30px rgba(40,20,10,.35)}}
.scl path{{fill:none;stroke:{CREAM};stroke-width:8;stroke-linecap:round;stroke-linejoin:round}}
.scl #panL path:last-child,.scl #panR path:last-child{{fill:{YEL};stroke:{YEL}}}
.scl .dot{{fill:{YEL}}}
.xx{{color:#ff8a7a;font-family:Inter;font-weight:600;font-size:46px}}
.stxt{{font:600 30px Montserrat;letter-spacing:5px;fill:#3a2620}}
.stc{{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;text-align:center;
  font:italic 400 88px 'Instrument Serif';line-height:.8;color:#3a2620}}
.orb{{position:absolute;left:0;top:0}}
.orb.b{{z-index:3;filter:brightness(.8)}}
.orb.f{{z-index:6}}
.opill{{padding:12px 24px;border-radius:99px;background:rgba(255,248,239,.95);color:#3a2620;font:600 36px Inter;white-space:nowrap;
  border:3px solid {YEL};box-shadow:0 16px 36px rgba(50,25,15,.35)}}
.tk circle{{fill:rgba(255,248,239,.95);stroke:{YEL};stroke-width:5}}
.tk path{{fill:none;stroke:#3a2620;stroke-width:8;stroke-linecap:round;stroke-linejoin:round}}
'''

SAFE_GUIDE = ('<div style="position:absolute;inset:0;z-index:99;pointer-events:none">'
              '<div style="position:absolute;left:0;right:0;top:0;height:220px;background:rgba(255,0,0,.28)"></div>'
              '<div style="position:absolute;left:0;right:0;top:1470px;bottom:0;background:rgba(255,0,0,.28)"></div>'
              '<div style="position:absolute;left:0;width:35px;top:220px;height:1250px;background:rgba(255,0,0,.28)"></div>'
              '<div style="position:absolute;right:0;width:35px;top:220px;height:935px;background:rgba(255,0,0,.28)"></div>'
              '<div style="position:absolute;right:0;width:100px;top:1155px;height:315px;background:rgba(255,0,0,.28)"></div></div>')


def build():
    for g in (g_hook, g_perfect, g_notperf, g_together, g_honest, g_excel, g_why, g_notonly, g_own, g_eight, g_belt, g_outro):
        g()
    captions()
    tweens = grades() + TW
    # v2: the renderer draws the GSAP layer ~2 frames behind the video (v1 cut check: a faint ghost of the previous
    # section's graphics on the first frame of each new shot), so every timeline position runs 2 frames early.
    lead = 2 / 30
    tweens = [re.sub(r',(\d+\.\d+)\);$', lambda m: f',{max(0.0, float(m.group(1)) - lead):.3f});', t) for t in tweens]
    nl = '\n'
    cut = ('<div id="cutwrap"><video id="cut" class="full g" src="assets/subject.webm" muted playsinline data-start="0" '
           f'data-media-start="0" data-duration="{DUR:.3f}" data-track-index="1"></video></div>') if os.path.exists('assets/subject.webm') else ''
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
{nl.join(audio())}
  <div id="stage">
    <video id="bgv" class="full g" src="assets/aroll.mp4" muted playsinline data-start="0" data-media-start="0" data-duration="{DUR:.3f}" data-track-index="0"></video>
{nl.join(HTML_BACK)}
    {cut}
  </div>
  <div id="gwarm" class="fx"></div><div id="gvig" class="fx"></div><div id="ggrad" class="fx"></div>
{nl.join(HTML_FRONT)}
{SAFE_GUIDE if SAFE else ''}
</div>
<script>
const tl = gsap.timeline({{ paused: true }});
{nl.join(TO)}
{nl.join(tweens)}
tl.set({{}}, {{}}, {DUR:.3f});
window.__timelines["main"] = tl;
</script>
</body>
</html>
'''


with open('index.html', 'w', encoding='utf-8', newline='\n') as _f:
    _f.write(build())
print(f'wrote index.html {DUR:.3f}s  cuts {[round(c, 3) for c in CUTS]}')
