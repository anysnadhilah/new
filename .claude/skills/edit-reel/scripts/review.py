"""Build the review for the latest render.

    review.py <project>                      # renders thumbnails, preview, the download; writes review/
    review.py <project> --assets map.json    # after uploading review/upload.json's files to the Studio's assets:
                                             # writes review/studio_doc.json for the Studio's reviews/<request id>

The review lives inside the Reel Studio (see SKILL.md, Step 9): review/studio.json (the data, with local file names),
review/upload.json (files to upload as Studio assets: preview, one thumbnail sprite, the download parts). map.json is
{"<file name>": {"id": "<asset id>", "url": "<asset url>"}} from the upload result. A standalone page (index.html +
files.json) is written too, for a setup without a Studio.

Claude then publishes it with the Artifact tool (see SKILL.md, Step 9) and later reads the viewer's
Keep / Change / Drop choices, caption fixes, look switch and timed notes back from the page's database.
"""
import json
import re
import subprocess
import sys
import time
from pathlib import Path

from PIL import Image

from common import SK, config, die, load_json, project_dir
from render import load_style, stills
from styles.base import Context

THUMB = (180, 320)
MAX_PREVIEW = 14 * 1024 * 1024          # stays under the 15 MB per-file publish limit
PART = 14 * 1024 * 1024                 # the download is published in parts this size; the page joins them

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


def final_parts(src, out):
    """The Instagram-ready file (1080x1920 H.264 high, 30 fps, AAC 48 kHz, fast start), cut into parts the page
    downloads and joins back into one .mp4. Returns the published part paths and the size."""
    dest = out / "final.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-vf", "scale=1080:1920:flags=lanczos,fps=30",
                    "-c:v", "libx264", "-preset", "slow", "-crf", "18", "-maxrate", "12M", "-bufsize", "24M",
                    "-profile:v", "high", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
                    "-movflags", "+faststart", str(dest)], check=True)
    pdir = out / "final"
    pdir.mkdir(exist_ok=True)
    for old in pdir.glob("part-*.mp4"):
        old.unlink()
    blob = dest.read_bytes()
    parts = []
    for i in range(0, len(blob), PART):
        f = pdir / f"part-{i // PART:02d}.mp4"
        f.write_bytes(blob[i:i + PART])
        parts.append(f"final/{f.name}")
    return parts, len(blob)


def fx_detail(spec):
    keys = [k for k in ("text", "label", "title", "prompt", "preset", "kicker") if spec.get(k)]
    bits = [f'{k} "{spec[k]}"' for k in keys]
    for k in ("items", "notes", "headlines", "messages", "doodles"):
        if spec.get(k):
            bits.append(f"{len(spec[k])} {k}")
    return ", ".join(bits)


def sprite(out, items, cols=8):
    """All thumbnails on one sheet (one upload instead of dozens); item["tile"] is its place."""
    rows = (len(items) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * THUMB[0], max(1, rows) * THUMB[1]), (20, 20, 20))
    for i, it in enumerate(items):
        sheet.paste(Image.open(out / it["thumb"]), ((i % cols) * THUMB[0], (i // cols) * THUMB[1]))
        it["tile"] = i
    sheet.save(out / "thumbs.jpg", quality=78)
    return {"file": "thumbs.jpg", "cols": cols, "count": len(items)}


def studio_doc(proj, map_path):
    out = proj / "review"
    data = json.loads((out / "studio.json").read_text())
    amap = json.loads(Path(map_path).read_text())
    url = lambda name: amap[Path(name).name]["url"]
    data["preview"] = url(data["preview"])
    data["thumbs"]["url"] = url(data["thumbs"].pop("file"))
    data["download"]["parts"] = [url(p) for p in data["download"]["parts"]]
    data["asset_ids"] = [v["id"] for v in amap.values()]
    doc = {"data": data, "updated": time.strftime("%Y-%m-%dT%H:%M:%S")}
    (out / "studio_doc.json").write_text(json.dumps(doc, ensure_ascii=False))
    print(f"studio doc: {out / 'studio_doc.json'} -> ArtifactData set on studioUrl, collection reviews, doc <request id>")


def main():
    proj = project_dir(sys.argv[1]) if len(sys.argv) > 1 else die("usage: review.py <project> [--assets map.json]")
    if "--assets" in sys.argv:
        return studio_doc(proj, sys.argv[sys.argv.index("--assets") + 1])
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
    sheet = sprite(out, items)

    preview(video, out / "preview.mp4")
    parts, size = final_parts(video, out)
    name = proj.name.replace("-", " ").replace("_", " ").title()
    data = {"name": name, "version": version, "style": plan.get("style", "it-girl"), "duration": tl["duration"],
            "built": time.strftime("%d %b %H:%M"), "cuts": cuts, "graphics": graphics, "captions": captions,
            "graphics_amount": plan.get("graphics", "medium"), "sfx": plan.get("sfx", "normal"),
            "studio": config().get("studioUrl"),
            "download": {"parts": parts, "size": size, "filename": f"{name} {version}.mp4"}}
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
    files.update({p: str(out / p) for p in parts})
    (out / "files.json").write_text(json.dumps(files, indent=2))
    studio = {**data, "preview": "preview.mp4", "thumbs": sheet}
    studio.pop("studio", None)
    for it in studio["cuts"] + studio["graphics"]:
        it.pop("thumb", None)
    (out / "studio.json").write_text(json.dumps(studio, ensure_ascii=False))
    (out / "upload.json").write_text(json.dumps([str(out / "preview.mp4"), str(out / "thumbs.jpg")] + [str(out / p) for p in parts], indent=1))
    mb = (out / "preview.mp4").stat().st_size / 1e6
    print(f"review page for {version}: {out / 'index.html'} ({len(cuts)} cuts, {len(graphics)} graphics, "
          f"{len(captions)} captions, preview {mb:.1f} MB)")
    print(f"studio: upload the {2 + len(parts)} files in review/upload.json as Studio assets, save the map, then review.py --assets <map>")
    print(f"standalone: file_path={out / 'index.html'}  files=<review/files.json>  capabilities={{\"db\": {{}}, \"comments\": {{}}}}"
          + (f"  url={info['url']}" if info.get("url") else "  (first publish: save the url into review/review.json)"))


if __name__ == "__main__":
    sys.exit(main())
