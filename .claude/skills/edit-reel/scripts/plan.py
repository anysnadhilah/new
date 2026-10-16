"""Draft plan.json (captions, punch words, hook, stickers) from timeline.json.

    plan.py <project> --style whimsical|it-girl|scrapbook [--force]

The draft is a starting point: Claude then fixes misheard words, picks better punch words, writes the
hook and places stickers by editing plan.json. Re-running without --force never overwrites edits.

plan.json:
{
  "style": "it-girl",
  "hook": {"text": "terlalu ambisius?", "label": "real talk", "start": 0.0, "end": 2.8},   # or null
  "captions": [{"start": 0.0, "end": 1.9, "emph": "ambisius",
                "words": [{"w": "sometimes", "s": 0.02, "e": 0.5}, ...]}],
  "stickers": [{"type": "heart", "at": 12.4, "dur": 1.6}],     # optional x, y (px) and text
  "zone": "auto"                                               # auto | top | bottom
}
"""
import argparse
import re
import sys

from common import config, load_json, project_dir, save_json

STYLES = ("whimsical", "it-girl", "scrapbook")
MAX_CHARS = {"whimsical": 20, "it-girl": 24, "scrapbook": 26}
MAX_WORDS = 4

# words that never make a good punch word (English + Malay fillers and function words)
STOP = set("""
a an the and or but so to of in on at for with from by is are was were be been it its this that these those
i im i'm you we they he she me my our your their them us not no yes just really very can will would should
could do does did have has had get got go going like then than there here what when where who why how all
some more most much many one two also too okay ok yeah um uh
saya aku kita kami awak dia mereka yang dan atau tapi untuk dengan dalam pada ke dari ini itu tu ni ada
adalah akan boleh nak buat lagi dah sudah je jer pun lah kan ke ka la macam so bila kalau lepas baru
dulu semua benda sangat banyak tak tidak bukan apa mana berapa sebab jadi daripada kepada tentang hari
same time thing things really actually just also something everything because
""".split())


def clean(w):
    return re.sub(r"[^\w'-]", "", w.lower())


def group_words(words, max_chars):
    groups, cur = [], []
    for i, w in enumerate(words):
        if cur:
            gap = w["s"] - cur[-1]["e"]
            text_len = len(" ".join(x["w"] for x in cur + [w]))
            ends_sentence = cur[-1]["w"].rstrip().endswith((".", "?", "!"))
            ends_clause = cur[-1]["w"].rstrip().endswith(",")
            if (gap > 0.3 or text_len > max_chars or len(cur) >= MAX_WORDS or ends_sentence
                    or (ends_clause and len(cur) >= 2) or w.get("seg") != cur[-1].get("seg")):
                groups.append(cur)
                cur = []
        cur.append(w)
    if cur:
        groups.append(cur)
    return groups


def pick_emph(group):
    best = max(group, key=lambda w: len(clean(w["w"])) if clean(w["w"]) not in STOP else 0)
    return clean(best["w"]) if len(clean(best["w"])) >= 7 else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("project")
    ap.add_argument("--style", default=config().get("defaultStyle", "it-girl"), choices=STYLES)
    ap.add_argument("--force", action="store_true", help="overwrite an existing plan.json")
    a = ap.parse_args()
    proj = project_dir(a.project)
    out = proj / "plan.json"
    if out.exists() and not a.force:
        plan = load_json(out)
        plan["style"] = a.style
        save_json(out, plan)
        print(f"plan.json exists (kept your edits); style set to {a.style}. Use --force to redraft.")
        return
    tl = load_json(proj / "timeline.json")
    words = []
    for si, seg in enumerate(tl["segments"]):
        for w in seg["words"]:
            if w["w"].strip():
                words.append({**w, "seg": si})
    if not words:
        print("no speech in this video: no captions (graphics can still be placed on the music's beats by autofx.py)")

    groups = group_words(words, MAX_CHARS[a.style]) if words else []
    starts = [round(max(g[0]["s"] - 0.06, 0), 3) for g in groups] + [tl["duration"]]
    caps = []
    for i, g in enumerate(groups):
        caps.append({
            "start": starts[i],
            "end": round(min(starts[i + 1], g[-1]["e"] + 0.7, tl["duration"]), 3),
            "emph": pick_emph(g) if i % 2 == 0 else None,
            "words": [{"w": w["w"], "s": w["s"], "e": w["e"]} for w in g],
        })
    plan = {"style": a.style, "hook": None, "captions": caps, "stickers": [], "zone": "auto"}
    save_json(out, plan)
    print(f"drafted {len(caps)} caption groups -> {out}")
    for c in caps:
        txt = " ".join(w["w"] for w in c["words"])
        print(f"[{c['start']:6.2f}-{c['end']:6.2f}] {txt}" + (f"   <{c['emph']}>" if c["emph"] else ""))


if __name__ == "__main__":
    sys.exit(main())
