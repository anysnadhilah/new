"""Style Lab: render look options on the user's own reel so they can pick them on the Reel Studio page.

    stylelab.py <project> [--style it-girl]

Writes <project>/stylelab/ : lab.json (tabs -> cards with an image, a title, a description and the plan.json
settings each card stands for) and one 360x640 jpg per card (transitions: a 3-frame strip). Publish the folder to
the Studio as files under lab/ (see SKILL.md, "Style Lab"); the viewer ticks "take" / "more like this" and the
choices land in the Studio database (collection lab, doc choices).
"""
import argparse
import copy
import json
import time

from PIL import Image

from common import load_json, project_dir
from styles.base import Context

PALETTES = [
    ("blush", "Blush", "very light pink to lilac (current)", "#FBD3E0", "#CDB8F2"),
    ("champagne", "Champagne", "soft gold and cream", "#F3D46A", "#FFF3C4"),
    ("lilac", "Lilac dream", "lilac with a rose second tone", "#D9C8FA", "#F6C2D3"),
    ("rose", "Dusty rose", "muted rose and nude", "#E8A9B6", "#F7E1D7"),
    ("ivory", "Ivory", "warm white, quiet luxury", "#FFF8EC", "#E9D8C4"),
    ("peach", "Peach sorbet", "peach with a pink second tone", "#FFC9A8", "#FBD3E0"),
]
FONTS = [
    ("playfair", "Playfair italic", "elegant italic titles, Playfair captions (current)", "PlayfairDisplay-Italic.ttf", "PlayfairDisplay-Regular.ttf"),
    ("instrument", "Instrument Serif", "tall condensed editorial serif", "InstrumentSerif-Regular.ttf", "InstrumentSerif-Regular.ttf"),
    ("fraunces", "Fraunces + Figtree", "soft bold italic titles, clean sans captions", "Fraunces-SemiBoldItalic.ttf", "Figtree-Medium.ttf"),
    ("script", "Sacramento script", "handwritten titles, Playfair captions", "Sacramento-Regular.ttf", "PlayfairDisplay-Regular.ttf"),
    ("modern", "Figtree bold", "modern sans, no serif at all", "Figtree-ExtraBold.ttf", "Figtree-Medium.ttf"),
    ("classic", "Tinos", "classic newspaper serif", "Tinos-Italic.ttf", "Tinos-Regular.ttf"),
]
CAPTIONS = [
    ("keyword", "Key word big", "the punch word set big in the accent italic, when there is room beside your face (current)"),
    ("phrase", "Calm phrases", "the whole phrase at one size, nothing jumps"),
    ("small", "Small subtitles", "quiet, smaller captions so the graphics lead"),
]


def pick_times(ctx, matte):
    """A good moment for look previews (a section title on screen) and windows for effect previews."""
    secs = [s for s in ctx.plan.get("sections", []) or []]
    t_look = (secs[0]["start"] + 1.3) if secs else ctx.duration * 0.3
    frames = sorted(matte)
    windows, run = [], []
    for f in frames:
        if run and f != run[-1] + 1:
            windows.append(run)
            run = []
        run.append(f)
    if run:
        windows.append(run)
    long = [w for w in windows if len(w) >= 75]
    t_cut = long[0][0] / 30 + 0.3 if long else None
    return t_look, t_cut


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("project")
    ap.add_argument("--style", default=None)
    a = ap.parse_args()
    proj = project_dir(a.project)
    plan = load_json(proj / "plan.json")
    tl = load_json(proj / "timeline.json")
    style_name = a.style or plan.get("style", "it-girl")
    out = proj / "stylelab"
    out.mkdir(exist_ok=True)
    for old in out.glob("*.jpg"):
        old.unlink()
    import render
    mj = proj / "work" / "matte.json"
    matte = set(load_json(mj)["frames"]) if mj.exists() else set()

    base = copy.deepcopy(plan)
    base["style"] = style_name
    base["effects"] = []                         # previews show one thing at a time
    ctx0 = Context(tl, base, proj)
    t_look, t_cut = pick_times(ctx0, matte)
    words = [w["w"].strip(",.?!").lower() for c in plan.get("captions", []) for w in c["words"]]
    secs = plan.get("sections", []) or []
    hook = (plan.get("hook") or {}).get("text", "come back")
    feeling = next((w for w in words if w in ("overwhelmed", "stress", "burnout", "penat", "tired", "stuck")),
                   hook.split()[-1].strip("?.!,"))

    def shot(name, p, t, size=(360, 640), roomy=False):
        ctx = Context(tl, p, proj)
        if roomy:                                   # show the look as it reads when there is room beside the face
            ctx.room = lambda _t: 5000
        style = render.load_style(p.get("style", style_name), ctx)
        img = render.stills(proj, style, ctx, [t])[0].resize(size, Image.LANCZOS)
        img.save(out / name, quality=82)
        return f"lab/{name}"

    def variant(**look):
        p = copy.deepcopy(base)
        p["look"] = {**(plan.get("look") or {}), **look}
        return p

    tabs = []
    cards = []
    for pid, title, desc, a1, a2 in PALETTES:
        cards.append({"id": f"pal-{pid}", "title": title, "desc": desc, "swatches": [a1, a2],
                      "img": shot(f"pal-{pid}.jpg", variant(accent=a1, accent2=a2), t_look),
                      "sets": {"look": {"accent": a1, "accent2": a2}}})
    tabs.append({"id": "palettes", "label": "Palettes", "hint": "The accent colours for key words, titles, stars and ovals.", "cards": cards})

    cards = []
    for fid, title, desc, tf, cf in FONTS:
        cards.append({"id": f"font-{fid}", "title": title, "desc": desc,
                      "img": shot(f"font-{fid}.jpg", variant(title_font=tf, caption_font=cf), t_look),
                      "sets": {"look": {"title_font": tf, "caption_font": cf}}})
    tabs.append({"id": "fonts", "label": "Fonts", "hint": "Title + caption pairs, written on your own video.", "cards": cards})

    # a moment where a caption's key word is on screen (so the three caption modes differ)
    t_cap = t_look + 3
    for c in plan.get("captions", []):
        e = (c.get("emph") or "").lower().strip(",.?!")
        hit = next((w for w in c["words"] if e and w["w"].lower().strip(",.?!") == e), None)
        if hit and len(c["words"]) >= 3 and c["start"] > t_look + 2 and not any(s["start"] <= c["start"] < s["start"] + 2.7 for s in secs):
            t_cap = min(c["end"] - 0.05, hit["e"] + 0.15)
            break
    cards = []
    for cid, title, desc in CAPTIONS:
        cards.append({"id": f"cap-{cid}", "title": title, "desc": desc,
                      "img": shot(f"cap-{cid}.jpg", variant(captions=cid), t_cap, roomy=True),
                      "sets": {"look": {"captions": cid}}})
    tabs.append({"id": "captions", "label": "Captions", "hint": "How the words you say appear.", "cards": cards})

    # effects: one effect at a time, each at a moment where it reads well
    t0 = t_cut or t_look
    titles = [s["title"] for s in secs][:4] or ["plan your week", "check your calendar", "count your hours", "pick 1-2 goals"]
    fx = [
        ("circle-title", "Oval title", "the method name in an oval that draws itself, with stars",
         {"type": "circle-title", "text": "come back|method"}, 1.4),
        ("peek-title", "Big word behind you", "one word peeking from behind your head",
         {"type": "peek-title", "text": feeling + "."}, 1.3),
        ("calendar", "Calendar", "a calendar app above you, days light up as you talk",
         {"type": "split-panel", "panel": "calendar"}, 2.8),
        ("popups", "Pop-up hook", "reminder windows pile up: the intro hook",
         {"type": "split-panel", "panel": "popups"}, 2.3),
        ("todo-scroll", "Endless to-do", "a to-do list that never stops scrolling",
         {"type": "split-panel", "panel": "todo-scroll"}, 1.9),
        ("time-bars", "Hours chart", "free hours per day grow as bars",
         {"type": "split-panel", "panel": "time-bars"}, 2.6),
        ("goals", "Goal cards", "only the goals you pick stay lit",
         {"type": "split-panel", "panel": "goals"}, 2.5),
        ("checklist", "Checklist recap", "your steps tick off one by one",
         {"type": "checklist", "title": "the method", "items": titles}, 3.0),
        ("punch-zoom", "Punch zoom + words", "a fast zoom on your face with the key line",
         {"type": "punch-zoom", "zoom": 1.3, "text": "the key line|right here"}, 0.9),
        ("dolly-zoom", "Dolly zoom", "the room moves while you stay still",
         {"type": "dolly-zoom", "amount": 0.4}, 1.4),
        ("doodle-outline", "Doodle outline", "a hand-drawn line traces around you",
         {"type": "doodle-outline", "doodles": ["sparkle", "heart"]}, 1.4),
        ("paper-cutout", "Paper cutout", "you as a paper cut-out on a collage page",
         {"type": "paper-cutout", "text": feeling[:6]}, 1.2),
    ]
    cards = []
    for i, (eid, title, desc, spec, at) in enumerate(fx):
        needs = eid in ("peek-title", "dolly-zoom", "doodle-outline", "paper-cutout") or spec["type"] == "split-panel"
        if needs and not t_cut and spec["type"] != "split-panel":
            continue
        p = copy.deepcopy(base)
        s0 = round(t0 if needs else t_look + 0.2, 2)
        p["effects"] = [{**spec, "start": s0, "end": s0 + 4.0}]
        cards.append({"id": f"fx-{eid}", "title": title, "desc": desc,
                      "img": shot(f"fx-{eid}.jpg", p, s0 + at), "sets": {"effect": eid}})
    tabs.append({"id": "effects", "label": "Effects", "hint": "Motion graphics, shown on your video. Take the ones you want in every reel.", "cards": cards})

    # transitions: three frames across a cut
    cut = next((c for c in ctx0.cuts if c > t_look), ctx0.cuts[0] if ctx0.cuts else 3.0)
    cards = []
    for tid, title, desc, times, spec in (
            ("zoom-through", "Zoom-through", "rush into the cut through a zoom blur", (cut - 0.12, cut, cut + 0.12),
             {"type": "zoom-through", "at": cut}),
            ("punch", "Punch-in", "each new idea lands with a small zoom", (cut - 0.1, cut + 0.03, cut + 0.3), None),
            ("none", "Clean cut", "no effect, just the cut", (cut - 0.1, cut + 0.05, cut + 0.3), None)):
        p = copy.deepcopy(base)
        if spec:
            p["effects"] = [spec]
        if tid == "none":
            p["sections"] = []
            p["hook"] = None
        ctx = Context(tl, p, proj)
        style = render.load_style(style_name, ctx)
        if tid == "none":
            style.cut_punch = 0
        frames = render.stills(proj, style, ctx, list(times))
        strip = Image.new("RGB", (3 * 240, 427), (20, 20, 20))
        for j, im in enumerate(frames):
            strip.paste(im.resize((236, 420), Image.LANCZOS), (j * 240 + 2, 3))
        strip.save(out / f"tr-{tid}.jpg", quality=82)
        cards.append({"id": f"tr-{tid}", "title": title, "desc": desc, "img": f"lab/tr-{tid}.jpg", "wide": True,
                      "sets": {"look": {"transition": tid}}})
    tabs.append({"id": "transitions", "label": "Transitions", "hint": "What happens between takes.", "cards": cards})

    lab = {"project": proj.name, "style": style_name, "built": time.strftime("%d %b %H:%M"), "tabs": tabs}
    (out / "lab.json").write_text(json.dumps(lab, indent=1))
    files = {"lab/lab.json": str(out / "lab.json")}
    files.update({f"lab/{f.name}": str(f) for f in sorted(out.glob("*.jpg"))})
    (out / "files.json").write_text(json.dumps(files, indent=1))
    print(f"style lab: {sum(len(t['cards']) for t in tabs)} cards in {out}  (publish files.json with the Studio)")


if __name__ == "__main__":
    main()
