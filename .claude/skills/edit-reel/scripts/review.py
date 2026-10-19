"""Build the review page for the latest render: <project>/review/ (index.html, thumbs/, preview.mp4).

    review.py <project>

Claude then publishes it with the Artifact tool (see SKILL.md, Step 9) and later reads the viewer's
Keep / Change / Drop choices, caption fixes, look switch and timed notes back from the page's database.
"""
import json
import re
import subprocess
import sys
import time

from PIL import Image

from common import SK, config, die, load_json, project_dir
from render import load_style, stills
from styles.base import Context

THUMB = (180, 320)
MAX_PREVIEW = 14 * 1024 * 1024          # stays under the 15 MB per-file publish limit

FX_NAMES = {"punch-zoom": "punch zoom", "zoom-through": "zoom-through cut", "phone-frame": "phone frame",
            "pull-back": "pull-back reveal", "app-split": "app split", "dolly-zoom": "dolly zoom",
            "checklist": "checklist", "phone-float": "floating phone", "note-wall": "note wall",
            "headline-wall": "headline wall", "chart-grow": "chart grow", "orbit": "orbit",
            "new-background": "new background", "paper-cutout": "paper cutout", "doodle-outline": "doodle outline",
            "cover-title": "cover title", "glass-title": "glass title"}


def latest_render(proj):
    vids = [p for p in (proj / "renders").glob(f"{proj.name}-v*.mp4") if re.fullmatch(rf"{re.escape(proj.name)}-v\d+\.mp4", p.name)]
    if not vids:
        die("no render yet: run render.py first")
    return max(vids, key=lambda p: int(re.search(r"-v(\d+)\.mp4$", p.name).group(1)))


def preview(src, dest):
    for crf in (28, 32, 36):
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-vf", "scale=540:960", "-c:v", "libx264",
                        "-preset", "medium", "-crf", str(crf), "-c:a", "aac", "-b:a", "96k", "-movflags", "+faststart",
                        str(dest)], check=True)
        if dest.stat().st_size <= MAX_PREVIEW:
            return
    die("preview is still over 14 MB; the reel is too long for the review page")


def fx_detail(spec):
    keys = [k for k in ("text", "label", "title", "prompt", "preset", "kicker") if spec.get(k)]
    bits = [f'{k} "{spec[k]}"' for k in keys]
    for k in ("items", "notes", "headlines", "messages", "doodles"):
        if spec.get(k):
            bits.append(f"{len(spec[k])} {k}")
    return ", ".join(bits)


def main():
    proj = project_dir(sys.argv[1]) if len(sys.argv) > 1 else die("usage: review.py <project>")
    plan = load_json(proj / "plan.json")
    tl = load_json(proj / "timeline.json")
    edl = load_json(proj / "edl.json")
    video = latest_render(proj)
    version = re.search(r"-(v\d+)\.mp4$", video.name).group(1)
    out = proj / "review"
    (out / "thumbs").mkdir(parents=True, exist_ok=True)
    for old in (out / "thumbs").glob("*.jpg"):
        old.unlink()

    cuts = []
    for i, seg in enumerate(tl["segments"]):
        src = next((e for e in edl if e.get("id") == seg["id"]), seg)
        cuts.append({"id": f"cut-{seg['id']}", "event": f"{i + 1:03d}", "clip": seg["clip"], "start": seg["start"],
                     "end": seg["end"], "src_in": src["in"], "src_out": src["out"], "zoom": seg.get("zoom", 1.0),
                     "line": " ".join(w["w"] for w in seg["words"]), "at": seg["start"] + min(0.6, (seg["end"] - seg["start"]) / 2)})

    graphics = []
    if plan.get("hook"):
        h = plan["hook"]
        graphics.append({"id": "hook", "kind": "Hook title", "title": h["text"], "start": h["start"], "end": h["end"],
                         "detail": " · ".join(x for x in (h.get("label"), h.get("sub")) if x)})
    for i, sec in enumerate(plan.get("sections", []) or []):
        graphics.append({"id": f"section-{i}", "kind": "Section title", "title": sec["title"], "start": sec["start"],
                         "end": sec["end"], "detail": " · ".join(x for x in (sec.get("kicker"), sec.get("sub")) if x)})
    for i, st in enumerate(plan.get("stickers", [])):
        graphics.append({"id": f"sticker-{i}", "kind": f"Sticker · {st.get('type', '')}", "start": st["at"],
                         "end": st["at"] + st.get("dur", 1.5), "title": st.get("text") or st.get("kind") or st.get("type", ""),
                         "detail": ""})
    for i, fx in enumerate(plan.get("effects", [])):
        start = fx["start"] if "start" in fx else fx.get("at", 0) - 0.22       # transitions sit on one cut ("at")
        end = fx["end"] if "end" in fx else fx.get("at", start) + 0.22
        graphics.append({"id": f"fx-{i}-{fx['type']}", "kind": f"Effect · {FX_NAMES.get(fx['type'], fx['type'])}",
                         "title": (fx.get("text") or fx.get("title") or fx.get("label") or FX_NAMES.get(fx["type"], fx["type"])).replace("|", " / "),
                         "start": start, "end": end, "detail": fx_detail(fx)})
    graphics.sort(key=lambda g: g["start"])
    for g in graphics:
        g["at"] = (g["start"] + g["end"]) / 2

    captions = []
    for i, c in enumerate(plan.get("captions", [])):
        captions.append({"id": f"cap-{i}", "start": c["start"], "end": c["end"], "emph": c.get("emph") or "",
                         "text": " ".join(w["w"] for w in c["words"])})

    # thumbnails: real finished frames (grade, effects and style layer)
    ctx = Context(tl, plan, proj)
    style = load_style(plan.get("style", "it-girl"), ctx)
    items = cuts + graphics
    t0 = time.time()
    frames = stills(proj, style, ctx, [it["at"] for it in items])
    for it, im in zip(items, frames):
        path = out / "thumbs" / f"{it['id']}.jpg"
        im.resize(THUMB, Image.LANCZOS).save(path, quality=80)
        it["thumb"] = f"thumbs/{it['id']}.jpg"
        del it["at"]
    print(f"{len(items)} thumbnails in {time.time() - t0:.0f}s", flush=True)

    preview(video, out / "preview.mp4")
    name = proj.name.replace("-", " ").replace("_", " ").title()
    data = {"name": name, "version": version, "style": plan.get("style", "it-girl"), "duration": tl["duration"],
            "built": time.strftime("%d %b %H:%M"), "cuts": cuts, "graphics": graphics, "captions": captions,
            "graphics_amount": plan.get("graphics", "medium"), "sfx": plan.get("sfx", "normal"),
            "studio": config().get("studioUrl")}
    ch_path = out / "changes.json"                 # what the last review changed (written by review_apply.py + Claude)
    ch = json.loads(ch_path.read_text()) if ch_path.exists() else {}
    if ch.get("from") and ch["from"] != version:
        data["changes"] = [{**c, "at": None if c.get("at") is None else min(float(c["at"]), tl["duration"] - 0.1)}
                           for c in ch.get("items", [])]
        data["changes"].sort(key=lambda c: (c["at"] is None, c["at"] or 0))
        data["changes_from"] = ch["from"]
    page = (SK / "assets" / "review" / "template.html").read_text()
    page = page.replace("__TITLE__", f"{name} Review")
    page = page.replace("__REVIEW_DATA__", json.dumps(data, ensure_ascii=False).replace("</", "<\\/"))
    (out / "index.html").write_text(page)

    info_path = out / "review.json"
    info = json.loads(info_path.read_text()) if info_path.exists() else {}
    info.update({"version": version, "built": data["built"]})
    info_path.write_text(json.dumps(info, indent=2))
    files = {f"thumbs/{p.name}": str(p) for p in sorted((out / "thumbs").glob("*.jpg"))}
    files["preview.mp4"] = str(out / "preview.mp4")
    (out / "files.json").write_text(json.dumps(files, indent=2))
    mb = (out / "preview.mp4").stat().st_size / 1e6
    print(f"review page for {version}: {out / 'index.html'} ({len(cuts)} cuts, {len(graphics)} graphics, "
          f"{len(captions)} captions, preview {mb:.1f} MB)")
    print(f"publish: file_path={out / 'index.html'}  files=<review/files.json>  capabilities={{\"db\": {{}}, \"comments\": {{}}}}"
          + (f"  url={info['url']}" if info.get("url") else "  (first publish: save the url into review/review.json)"))


if __name__ == "__main__":
    sys.exit(main())
