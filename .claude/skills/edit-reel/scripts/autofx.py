"""Place motion graphics automatically from what is said: effects + style stickers, at a chosen amount.

    autofx.py <project> [--amount light|medium|max] [--no-cutout]

Reads plan.json (captions with word times) and timeline.json (cuts), writes "effects" and "stickers" back into
plan.json. Items it writes carry "auto": true; anything without it (added by hand) is kept and never overlapped.
Re-running replaces only the auto items. The result is a first pass: Claude then rewrites texts so they read
well (checklist items, phone messages, titles) and removes anything that does not fit the story.

Understands English and Malay cue words (numbers, lists, questions, feelings, apps, methods, growth).
"""
import argparse
import re
import sys

from common import load_json, project_dir, save_json
from plan import STOP

GAP = {"light": 14.0, "medium": 7.0, "max": 1.5}        # longest idle time (no graphic on screen) we allow
MIN_SPACE = 0.3                                          # never closer than this to another graphic
TRANSITION = "zoom-through"                              # a 0.4 s cut transition: stickers may overlap it

NUM_WORDS = set("""one two three four five six seven eight nine ten hundred thousand million first second third
satu dua tiga empat lima enam tujuh lapan sembilan sepuluh seratus ribu juta pertama kedua ketiga""".split())
LIST = set("""first second third step steps finally lastly tip tips pertama kedua ketiga langkah
akhirnya""".split())
FEEL = set("""overwhelmed overwhelm stress stressed tired burnout breakdown anxious anxiety sad happy love crazy amazing
wow scared afraid penat letih stres sedih gembira suka takut gila best seronok risau""".split())
APP = set("""app apps phone calendar kalendar notes note message messages dm whatsapp instagram tiktok email google
telefon aplikasi mesej schedule jadual""".split())
TITLE = set("""method secret rule rules system framework formula hack rahsia kaedah teknik sistem formula
peraturan""".split())
GROW = set("""grow growth grew increase increased double doubled scale revenue sales followers income profit naik
meningkat bertambah jualan pendapatan untung""".split())
CHANGE = set("""imagine instead before after dulu sekarang bayangkan""".split())


def span(e):
    """(start, end) of an effect; zoom-through only has "at" (the cut)."""
    if "start" in e:
        return e["start"], e.get("end", e["start"] + 2.5)
    return e["at"] - 0.25, e["at"] + 0.25


def beats(proj, dur, min_gap=0.45):
    """Strong onsets in the a-roll's audio (music hits, claps), for videos with little or no speech."""
    import subprocess
    import numpy as np
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(proj / "work" / "aroll.mkv"), "-ac", "1", "-ar", "22050",
                          "-f", "s16le", "-"], capture_output=True).stdout
    x = np.frombuffer(raw, "<i2").astype(np.float32) / 32768
    if len(x) < 22050:
        return []
    hop = 512
    frames = len(x) // hop
    e = np.array([np.sum(np.abs(np.diff(x[i * hop:(i + 1) * hop]))) for i in range(frames)])   # crude flux
    flux = np.maximum(0, np.diff(e, prepend=e[0]))
    thr = flux.mean() + 1.6 * flux.std()
    out, last = [], -1e9
    for i in range(1, frames - 1):
        t = i * hop / 22050
        if flux[i] > thr and flux[i] >= flux[i - 1] and flux[i] >= flux[i + 1] and t - last >= min_gap and t < dur - 0.5:
            out.append(round(t, 3))
            last = t
    return out


def norm(w):
    return re.sub(r"[^\w%$]", "", w.lower())


def is_num(w):
    return bool(re.search(r"\d", w)) or norm(w) in NUM_WORDS or "%" in w or w.startswith(("$", "RM"))


def caption_text(c):
    return " ".join(w["w"] for w in c["words"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("project")
    ap.add_argument("--amount", choices=list(GAP), default=None)
    ap.add_argument("--no-cutout", action="store_true", help="skip effects that need the speaker cut out (faster)")
    a = ap.parse_args()
    proj = project_dir(a.project)
    plan = load_json(proj / "plan.json")
    tl = load_json(proj / "timeline.json")
    amount = a.amount or plan.get("graphics", "medium")
    plan["graphics"] = amount
    cutout = not a.no_cutout and amount != "light"
    style = plan.get("style", "it-girl")
    caps = plan.get("captions", [])
    dur = tl["duration"]

    manual_fx = [e for e in plan.get("effects", []) if not e.get("auto")]
    manual_st = [s for s in plan.get("stickers", []) if not s.get("auto")]
    taken = [(*span(e), e["type"] == TRANSITION) for e in manual_fx]
    taken += [(s["at"], s["at"] + s.get("dur", 1.5), False) for s in manual_st]
    if plan.get("hook"):
        taken.append((plan["hook"]["start"], plan["hook"]["end"], False))

    def free(s, e, sticker=False, transition=False):
        return s >= 0 and e <= dur and all(e + MIN_SPACE <= a0 or s >= b0 + MIN_SPACE
                                           for a0, b0, tr in taken if not ((sticker or transition) and tr))

    fx, st = [], []
    used_types = {}

    def add_fx(spec):
        s, e = span(spec)
        if not free(s, e, transition=spec["type"] == TRANSITION):
            return False
        if spec["type"] != TRANSITION and e - s < 1.2:          # too short to read
            return False
        if spec.get("text") and any(f.get("text") == spec["text"] and f["type"] == spec["type"] for f in fx):
            return False
        if used_types.get(spec["type"], 0) >= {"light": 1, "medium": 2, "max": 4}[amount]:
            return False
        spec["auto"] = True
        fx.append(spec)
        taken.append((s, e, spec["type"] == TRANSITION))
        used_types[spec["type"]] = used_types.get(spec["type"], 0) + 1
        return True

    def add_st(spec):
        s, e = spec["at"], spec["at"] + spec.get("dur", 1.6)
        if not free(s, e, sticker=True):
            return False
        spec["auto"] = True
        st.append(spec)
        taken.append((s, e, False))
        return True

    # ---- hook: the opening line, if the plan has none yet
    if not plan.get("hook") and caps:
        first = caps[0]
        text = caption_text(first)
        plan["hook"] = {"text": " ".join(text.split()[:5]).strip(",."), "start": 0.0,
                        "end": round(min(3.0, max(1.8, first["end"] + 0.4)), 2), "auto": True}
        taken.append((0.0, plan["hook"]["end"], False))

    # ---- cue-driven effects, strongest cues first
    for i, c in enumerate(caps):
        words = [norm(w["w"]) for w in c["words"]]
        text = caption_text(c)
        s0, e0 = c["start"], c["end"]
        nxt = caps[i + 1: i + 4]
        if any(w in GROW for w in words) and cutout:
            add_fx({"type": "chart-grow", "start": s0, "end": min(dur, s0 + 3.2), "label": (c.get("emph") or words[-1]) + " ↗"})
        elif any(is_num(w["w"]) for w in c["words"]):
            num = " ".join(w["w"] for w in c["words"] if is_num(w["w"]))
            rest = [w["w"] for w in c["words"] if not is_num(w["w"])][:2]
            add_fx({"type": "punch-zoom", "start": s0, "end": min(e0 + 0.6, s0 + 2.4), "zoom": 1.28,
                    "text": f"{num}|{' '.join(rest)}".strip("|")})
        elif any(w in LIST for w in words) and len(nxt) >= 2:
            items = [" ".join(caption_text(n).split()[:5]).strip(",.") for n in nxt[:3]]
            add_fx({"type": "checklist", "start": s0, "end": min(dur, nxt[-1]["end"] + 0.4), "title": "all you need to do",
                    "items": items, "at": [n["start"] + 0.2 for n in nxt[:3]]})
        elif any(w in APP for w in words):
            add_fx({"type": "phone-float", "start": s0, "end": min(dur, s0 + 3.0), "title": "notes",
                    "messages": [text] + [caption_text(n) for n in nxt[:1]]})
        elif any(w in TITLE for w in words) and cutout:
            word = next((w["w"] for w in c["words"] if norm(w["w"]) in TITLE), c.get("emph") or text.split()[-1])
            add_fx({"type": "glass-title" if i % 2 else "cover-title", "start": s0, "end": min(dur, s0 + 2.6),
                    "text": norm(word).upper()})
        elif any(w in FEEL for w in words) and cutout:
            add_fx({"type": "headline-wall" if i % 2 else "note-wall", "start": s0, "end": min(dur, s0 + 2.8),
                    "headlines": [text] + [caption_text(n) for n in nxt[:3]], "notes": [text] + [caption_text(n) for n in nxt[:3]]})
        elif any(w in CHANGE for w in words) and cutout:
            add_fx({"type": "dolly-zoom" if i % 2 else "new-background", "start": s0, "end": min(dur, s0 + 2.2)})
        elif text.rstrip().endswith("?"):
            add_fx({"type": "punch-zoom", "start": s0, "end": min(e0 + 0.5, s0 + 2.2), "zoom": 1.25})

    # ---- transitions on cuts, ending reveal
    cuts = [s["start"] for s in tl["segments"][1:]]
    every = {"light": 6, "medium": 3, "max": 2}[amount]
    for k, c in enumerate(cuts):
        if k % every == 0:
            add_fx({"type": "zoom-through", "at": round(c, 3)})
    if amount != "light" and dur > 15:
        add_fx({"type": "pull-back", "start": round(dur - 3.6, 2), "end": round(dur, 2), "title": f"{proj.name}.mp4",
                "items": ["picked the best takes", "cut the dead air", "captions added", "graphics added"],
                "count": tl["frames"], "label": "frames edited"})

    # ---- rhythm: wherever nothing has happened for a while, add the next graphic from a rotation,
    # on that moment's punch word (or its longest word)
    gems = ["chrome-star", "jelly-flower-pink", "rhinestone-heart", "disco", "gold-star", "holo-heart", "sequin",
            "chrome-sparkle", "jelly-flower-lilac", "rhinestone-flower"]
    rotation = {
        "light": ["sticker", "punch-zoom", "sticker"],
        "medium": ["sticker", "punch-zoom", "sticker", "doodle-outline", "sticker", "glass-title"],
        "max": ["sticker", "punch-zoom", "glass-title", "sticker", "doodle-outline", "orbit", "sticker",
                "paper-cutout", "cover-title", "sticker", "new-background", "punch-zoom"],
    }[amount]
    if not cutout:
        rotation = [r for r in rotation if r in ("sticker", "punch-zoom")]
    turn = 0

    def key_word(c):
        if c.get("emph"):
            return c["emph"]
        good = [w["w"].strip(",.?!") for w in c["words"] if norm(w["w"]) not in STOP and len(norm(w["w"])) >= 4]
        return max(good, key=len, default="")

    def sticker(c, i):
        word = key_word(c)
        if style == "scrapbook":
            return {"type": "gem", "kind": gems[i % len(gems)], "at": round(c["start"], 2), "dur": 1.5, "size": 150}
        if style == "whimsical":
            return {"type": "pill-yellow" if i % 2 else "pill", "text": word, "at": round(c["start"], 2), "dur": 1.5}
        return {"type": "italic" if i % 2 else "chapter", "text": word, "at": round(c["start"], 2), "dur": 1.5}

    last = 0.0
    for i, c in enumerate(caps):
        busy = [b for a0, b, tr in taken if a0 <= c["start"] and not tr]
        last = max([last] + busy)
        if c["start"] - last < GAP[amount] or not key_word(c):
            continue
        for _ in range(len(rotation)):
            kind = rotation[turn % len(rotation)]
            turn += 1
            word = key_word(c)
            s0 = round(c["start"], 2)
            if kind == "sticker":
                ok = add_st(sticker(c, i))
            elif kind == "punch-zoom":
                ok = add_fx({"type": "punch-zoom", "start": s0, "end": min(dur, s0 + 1.8), "zoom": 1.25, "text": word})
            elif kind in ("glass-title", "cover-title"):
                ok = s0 + 2.3 <= dur and add_fx({"type": kind, "start": s0, "end": s0 + 2.3,
                                                 "text": norm(word).upper()[:10]})
            elif kind == "paper-cutout":
                ok = add_fx({"type": kind, "start": s0, "end": min(dur, s0 + 2.4), "text": norm(word)[:6]})
            elif kind == "new-background":
                ok = add_fx({"type": kind, "start": s0, "end": min(dur, s0 + 2.4), "preset": "studio"})
            else:
                ok = add_fx({"type": kind, "start": s0, "end": min(dur, s0 + 2.4)})
            if ok:
                last = c["start"] + 1.8
                break

    # ---- little or no speech: put graphics on the music's beats instead
    if sum(c["end"] - c["start"] for c in caps) < dur * 0.25:
        decor = {"scrapbook": "gem", "whimsical": "asterisk", "it-girl": None}.get(style)
        last = -1e9
        for k, b in enumerate(beats(proj, dur)):
            if b - last < GAP[amount] + 1.2:
                continue
            if decor and k % 2 == 0:
                spec = {"type": decor, "at": b, "dur": 1.4}
                if decor == "gem":
                    spec.update(kind=gems[k % len(gems)], size=150)
                ok = add_st(spec)
            else:
                ok = add_fx({"type": "punch-zoom", "start": b, "end": min(dur, b + 1.3), "zoom": 1.18})
            if ok:
                last = b

    plan["effects"] = sorted(manual_fx + fx, key=lambda e: span(e)[0])
    plan["stickers"] = sorted(manual_st + st, key=lambda s: s["at"])
    save_json(proj / "plan.json", plan)
    need = sorted({e["type"] for e in plan["effects"] if e["type"] in (
        "dolly-zoom", "note-wall", "headline-wall", "chart-grow", "orbit", "new-background", "paper-cutout",
        "doodle-outline", "cover-title", "glass-title")})
    print(f"{amount}: {len(fx)} effects + {len(st)} stickers placed automatically "
          f"({len(manual_fx)} effects and {len(manual_st)} stickers by hand kept)")
    for e in fx:
        print(f"  {span(e)[0]:6.2f}s  {e['type']}  {e.get('text') or e.get('title') or e.get('label') or ''}")
    for s in st:
        print(f"  {s['at']:6.2f}s  sticker {s['type']}  {s.get('text') or s.get('kind') or ''}")
    if need:
        print("needs the cutout: run cutout.py (" + ", ".join(need) + ")")


if __name__ == "__main__":
    sys.exit(main())
