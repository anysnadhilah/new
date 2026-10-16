"""Apply the mechanical part of a review exported from the review page.

    review_apply.py <project> <export_dir>

<export_dir> is where Claude saved the page's database with ArtifactData list + out_dir
(decisions/<id>.json, notes/<id>.json, meta/look.json, meta/status.json).

Done automatically:
  - Drop on a cut: the take leaves edl.json; everything after it in plan.json moves earlier by its length,
    captions inside it go.
  - Drop on a graphic: the hook, sticker or effect leaves plan.json.
  - Caption fixes: the new words replace the old ones, spread over the same time span.
  - Look: plan.json "style" switches.
Printed for Claude to do by hand (needs judgement): every Change with its note, and every open timed note.
Writes work/review_todo.json with that list. Then: assemble (if cuts changed), cutout (if effects need it),
render, check, review.py, publish to the same url.
"""
import json
import sys
from pathlib import Path

from common import die, load_json, project_dir, save_json


def read_dir(path):
    out = {}
    if path.exists():
        for f in sorted(path.glob("*.json")):
            out[f.stem] = json.loads(f.read_text())
    return out


def respread(words, text):
    """New caption words spread over the old words' time span, proportional to their length."""
    new = text.split()
    if not new or not words:
        return words
    s, e = words[0]["s"], words[-1]["e"]
    total = sum(len(w) + 1 for w in new)
    out, t = [], s
    for w in new:
        d = (e - s) * (len(w) + 1) / total
        out.append({"w": w, "s": round(t, 3), "e": round(t + d, 3)})
        t += d
    return out


def main():
    if len(sys.argv) < 3:
        die(__doc__)
    proj = project_dir(sys.argv[1])
    exp = Path(sys.argv[2])
    plan = load_json(proj / "plan.json")
    edl = load_json(proj / "edl.json")
    tl = load_json(proj / "timeline.json")
    info = load_json(proj / "review" / "review.json", default={})
    version = info.get("version")

    decisions = {k: v for k, v in read_dir(exp / "decisions").items() if v.get("v") in (None, version)}
    notes = read_dir(exp / "notes")
    meta = read_dir(exp / "meta")
    done, todo = [], []

    # ---- captions first (their ids are positions in the current plan)
    caps = plan.get("captions", [])
    for k, d in decisions.items():
        if k.startswith("cap-") and d.get("text"):
            i = int(k[4:])
            if i < len(caps):
                old = " ".join(w["w"] for w in caps[i]["words"])
                caps[i]["words"] = respread(caps[i]["words"], d["text"])
                if caps[i].get("emph") and caps[i]["emph"].lower() not in d["text"].lower():
                    caps[i]["emph"] = None
                done.append(f'caption {i}: "{old}" -> "{d["text"]}"')

    # ---- graphics drops / changes
    effects = plan.get("effects", [])
    stickers = plan.get("stickers", [])
    drop_fx, drop_st = set(), set()
    for k, d in decisions.items():
        status, note = d.get("status"), (d.get("note") or "").strip()
        if k == "hook":
            if status == "drop":
                plan["hook"] = None
                done.append("hook removed")
            elif status == "change":
                todo.append({"what": "hook", "current": plan.get("hook"), "note": note})
        elif k.startswith("sticker-"):
            i = int(k.split("-")[1])
            if status == "drop":
                drop_st.add(i)
            elif status == "change" and i < len(stickers):
                todo.append({"what": f"sticker {i}", "current": stickers[i], "note": note})
        elif k.startswith("fx-"):
            i = int(k.split("-")[1])
            if status == "drop":
                drop_fx.add(i)
            elif status == "change" and i < len(effects):
                todo.append({"what": f"effect {i} ({effects[i]['type']})", "current": effects[i], "note": note})
    for i in sorted(drop_fx):
        done.append(f"effect removed: {effects[i]['type']} at {effects[i].get('start', effects[i].get('at'))}s")
    for i in sorted(drop_st):
        done.append(f"sticker removed: {stickers[i].get('type')} at {stickers[i]['at']}s")
    plan["effects"] = [e for i, e in enumerate(effects) if i not in drop_fx]
    plan["stickers"] = [s for i, s in enumerate(stickers) if i not in drop_st]

    # ---- cut drops: remove the take and pull everything after it earlier
    segs = tl["segments"]
    dropped = [s for s in segs if decisions.get(f"cut-{s['id']}", {}).get("status") == "drop"]
    for s in segs:
        d = decisions.get(f"cut-{s['id']}", {})
        if d.get("status") == "change":
            todo.append({"what": f"take {s['id']} ({s['clip']} {s['in']}-{s['out']}s)", "line": " ".join(w["w"] for w in s["words"]),
                         "note": (d.get("note") or "").strip()})
    if dropped:
        def shift(t):
            out = t
            for s in dropped:
                if t >= s["end"]:
                    out -= s["end"] - s["start"]
                elif t >= s["start"]:
                    return None                     # inside a removed take
            return round(out, 3)

        kept = []
        for c in plan.get("captions", []):
            st, en = shift(c["start"]), shift(c["end"] - 1e-3)
            if st is None or en is None:
                continue
            c["start"], c["end"] = st, round(en + 1e-3, 3)
            c["words"] = [{**w, "s": shift(w["s"]), "e": shift(w["e"] - 1e-3)} for w in c["words"]]
            c["words"] = [w for w in c["words"] if w["s"] is not None and w["e"] is not None]
            if c["words"]:
                kept.append(c)
        plan["captions"] = kept
        for coll, keys in ((plan.get("effects", []), ("start", "end", "at")), (plan.get("stickers", []), ("at",))):
            survivors = []
            for item in coll:
                moved = {k: shift(item[k]) for k in keys if k in item}
                if any(v is None for v in moved.values()):
                    done.append(f"{item.get('type')} at {item.get('start', item.get('at'))}s removed with its take")
                    continue
                item.update(moved)
                survivors.append(item)
            coll[:] = survivors
        if plan.get("hook"):
            hs = shift(plan["hook"]["start"])
            if hs is None:
                plan["hook"] = None
            else:
                plan["hook"]["end"] = round(hs + plan["hook"]["end"] - plan["hook"]["start"], 3)
                plan["hook"]["start"] = hs
        ids = {s["id"] for s in dropped}
        edl[:] = [e for e in edl if e.get("id") not in ids]
        for s in dropped:
            done.append(f"take {s['id']} removed ({s['end'] - s['start']:.1f}s): \"{' '.join(w['w'] for w in s['words'])[:60]}\"")

    # ---- look
    look = meta.get("look", {})
    if look.get("style") and look.get("v") in (None, version) and look["style"] != plan.get("style"):
        done.append(f"look: {plan.get('style')} -> {look['style']}")
        plan["style"] = look["style"]

    # ---- graphics amount and sound level
    mix = meta.get("mix", {})
    rerun_autofx = False
    if mix.get("v") in (None, version):
        if mix.get("sfx") and mix["sfx"] != plan.get("sfx", "normal"):
            done.append(f"sound effects: {plan.get('sfx', 'normal')} -> {mix['sfx']}")
            plan["sfx"] = mix["sfx"]
        if mix.get("graphics") and mix["graphics"] != plan.get("graphics", "medium"):
            done.append(f"motion graphics: {plan.get('graphics', 'medium')} -> {mix['graphics']} (run autofx.py)")
            plan["graphics"] = mix["graphics"]
            rerun_autofx = True

    # ---- notes
    for nid, n in notes.items():
        if not n.get("done"):
            todo.append({"what": "note", "id": nid, "at": n.get("t"), "note": n.get("text", "")})

    # a Change on something that a dropped take already removed is moot
    alive = [json.dumps(x, sort_keys=True) for x in plan.get("effects", []) + plan.get("stickers", [])]
    todo = [t for t in todo if not (isinstance(t.get("current"), dict) and "type" in t["current"]
                                    and t["what"] != "hook" and json.dumps(t["current"], sort_keys=True) not in alive)]

    save_json(proj / "plan.json", plan)
    save_json(proj / "edl.json", edl)
    save_json(proj / "work" / "review_todo.json", {"cuts_changed": bool(dropped), "autofx": rerun_autofx,
                                                    "done": done, "todo": todo})
    print("APPLIED:")
    for d in done or ["(nothing mechanical)"]:
        print("  -", d)
    print("TO DO BY HAND (edit edl.json / plan.json, then reply to each note):")
    for t in todo or [{"what": "(nothing)", "note": ""}]:
        print("  -", t["what"], (f"@ {t['at']}s" if t.get("at") is not None else ""), "->", t.get("note", ""))
    print("NEXT:", "assemble.py, " if dropped else "", "autofx.py, " if rerun_autofx else "",
          "cutout.py (if effects need it), render.py, check.py, review.py, publish")


if __name__ == "__main__":
    sys.exit(main())
