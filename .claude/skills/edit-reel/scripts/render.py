"""Render the reel: graded a-roll + the style's animated layer + sound effects.

    render.py <project> [--style NAME] [--safe] [--draft]
    render.py <project> --at 1.2,4.5,9    # quick stills with the style applied -> work/snap.jpg

Full renders go to renders/<project>-vN.mp4 (full quality) and renders/<project>-vN-phone.mp4 (720p).
--safe draws the red Reels safe-area guide; --draft encodes faster at slightly lower quality.
"""
import argparse
import importlib
import subprocess
import sys
import time
import wave

import numpy as np
from PIL import Image, ImageDraw

from common import FPS, H, SFX, SR, W, die, load_json, project_dir
from gfx import font
from effects import Matte, any_hides_captions, compose, load_effects, reserved_zone
from effects.sound import effect_sounds, level as sound_level
from styles.base import Context, blank, safe_guides

STYLES = {"whimsical": "styles.whimsical", "it-girl": "styles.it_girl", "scrapbook": "styles.scrapbook"}


def load_style(name, ctx):
    if name not in STYLES:
        die(f"unknown style {name}; choose from {', '.join(STYLES)}")
    return importlib.import_module(STYLES[name]).STYLE(ctx)


def load_sound(name, proj):
    """A sound by name: the project's own file (<project>/sfx/<name>.wav|.mp3) wins over the built-in one."""
    for ext in (".wav", ".mp3", ".m4a"):
        own = proj / "sfx" / f"{name}{ext}"
        if own.exists():
            raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(own), "-ac", "1", "-ar", str(SR), "-f", "s16le", "-"],
                                 capture_output=True, check=True).stdout
            return np.frombuffer(raw, "<i2").astype(np.float32) / 32768
    with wave.open(str(SFX / f"{name}.wav")) as f:
        return np.frombuffer(f.readframes(f.getnframes()), "<i2").astype(np.float32) / 32768


def sound_events(style, ctx, plan):
    """Style sounds (captions, stickers, hook, cuts) + effect sounds, scaled by the plan's sfx level."""
    k = sound_level(plan)
    events = list(style.sfx())
    for e in load_effects({"effects": ctx.effects}, ctx=ctx):
        events += effect_sounds(e)
    return [(at, name, gain * k) for at, name, gain in events if k > 0]


def sfx_track(events, duration, path, proj):
    n = int(duration * SR) + SR
    mix = np.zeros(n, np.float32)
    cache = {}
    for at, name, gain in events:
        if name not in cache:
            cache[name] = load_sound(name, proj)
        s = cache[name]
        i = max(0, int(at * SR))
        j = min(n, i + len(s))
        if j > i:
            mix[i:j] += s[: j - i] * gain
    mix = np.clip(mix[: int(duration * SR)], -1, 1)
    with wave.open(str(path), "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(SR)
        f.writeframes((mix * 32767).astype("<i2").tobytes())


def next_version(proj):
    n = 1
    while (proj / "renders" / f"{proj.name}-v{n}.mp4").exists():
        n += 1
    return proj / "renders" / f"{proj.name}-v{n}.mp4"


def full(proj, style, ctx, safe, draft):
    """Frame-locked render: ffmpeg decodes + grades the a-roll, Python composites the style layer onto each
    frame, a second ffmpeg encodes. Audio (voice + effects) is mixed and muxed in a final pass."""
    work = proj / "work"
    sfx_path = work / "sfx.wav"
    sfx_track(sound_events(style, ctx, ctx.plan), ctx.duration, sfx_path, proj)
    out = next_version(proj)
    silent = work / "video_only.mp4"
    dec = subprocess.Popen(["ffmpeg", "-v", "error", "-i", str(work / "aroll.mkv"), "-filter_complex", style.grade(),
                            "-map", "[bg]", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                            "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "veryfast" if draft else "medium",
                            "-crf", "21" if draft else "17", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(silent)],
                           stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    size = W * H * 3
    effects = load_effects({"effects": ctx.effects}, ctx=ctx)
    matte = Matte(work)
    t0 = time.time()
    for f in range(ctx.frames):
        raw = dec.stdout.read(size)
        if len(raw) < size:
            die(f"a-roll ended early at frame {f} of {ctx.frames}: {dec.stderr.read().decode()[-800:]}")
        t = f / FPS
        frame = None
        if any(e.active(t) for e in effects):
            frame = compose(Image.frombytes("RGB", (W, H), raw), t, effects, matte)
        style.hide_captions = any_hides_captions(effects, t)
        style.reserved = reserved_zone(effects, t)
        layer = blank()
        style.draw(layer, t)
        if safe:
            safe_guides(layer)
        box = layer.getbbox()
        if box:
            frame = frame or Image.frombytes("RGB", (W, H), raw)
            part = layer.crop(box)
            frame.paste(part, box[:2], part)
        enc.stdin.write(frame.tobytes() if frame is not None else raw)
        if f % (FPS * 5) == 0 and f:
            print(f"  {f / FPS:5.1f}s / {ctx.duration:.1f}s  ({time.time() - t0:.0f}s elapsed)", flush=True)
    enc.stdin.close()
    dec.stdout.close()
    dec.wait()
    if enc.wait() != 0:
        die(f"encoding failed: {enc.stderr.read().decode()[-1500:]}")
    audio = (f"[1:a]loudnorm=I=-14:TP=-1.5:LRA=11,aresample={SR}[vo];[2:a]aformat=channel_layouts=stereo[fx];"
             f"[vo][fx]amix=inputs=2:normalize=0:duration=first,alimiter=limit=0.84:level=0:attack=2:release=60[a]")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(silent), "-i", str(work / "aroll.mkv"), "-i", str(sfx_path),
                    "-filter_complex", audio, "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                    "-shortest", "-movflags", "+faststart", str(out)], check=True)
    phone = out.with_name(out.stem + "-phone.mp4")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(out), "-vf", "scale=720:1280", "-c:v", "libx264",
                    "-preset", "medium", "-crf", "23", "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart",
                    str(phone)], check=True)
    print(f"rendered {out}  ({time.time() - t0:.0f}s)\nphone copy {phone}")


def stills(proj, style, ctx, times, safe=False):
    """Finished frames (grade + effects + style layer) at the given times, as full-size RGB images."""
    work = proj / "work"
    effects = load_effects({"effects": ctx.effects}, ctx=ctx)
    matte = Matte(work)
    out = []
    for t in times:
        frame = work / "snap_frame.png"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.3f}", "-i", str(work / "aroll.mkv"),
                        "-filter_complex", style.grade(), "-map", "[bg]", "-frames:v", "1", str(frame)], check=True)
        base = compose(Image.open(frame).convert("RGB"), t, effects, matte).convert("RGBA")
        style.hide_captions = any_hides_captions(effects, t)
        style.reserved = reserved_zone(effects, t)
        canvas = blank()
        style.draw(canvas, t)
        safe_guides(canvas) if safe else None
        base.alpha_composite(canvas)
        out.append(base.convert("RGB"))
    return out


def snapshots(proj, style, ctx, times, safe):
    work = proj / "work"
    thumbs = [(t, im.resize((W // 3, H // 3), Image.LANCZOS)) for t, im in zip(times, stills(proj, style, ctx, times, safe))]
    cols = min(4, len(thumbs))
    rows = (len(thumbs) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * W // 3, rows * (H // 3 + 30)), "#111")
    d = ImageDraw.Draw(sheet)
    for i, (t, im) in enumerate(thumbs):
        x, y = (i % cols) * W // 3, (i // cols) * (H // 3 + 30)
        sheet.paste(im, (x, y + 30))
        d.text((x + 8, y + 4), f"{t:.2f}s", fill="#fff", font=font("Jost-Medium.ttf", 20))
    sheet.save(work / "snap.jpg", quality=88)
    print(f"wrote {work / 'snap.jpg'}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("project")
    ap.add_argument("--style")
    ap.add_argument("--safe", action="store_true")
    ap.add_argument("--draft", action="store_true")
    ap.add_argument("--at", help="comma-separated times for quick stills instead of a full render")
    a = ap.parse_args()
    proj = project_dir(a.project)
    plan = load_json(proj / "plan.json")
    tl = load_json(proj / "timeline.json")
    ctx = Context(tl, plan, proj)
    style = load_style(a.style or plan.get("style", "it-girl"), ctx)
    if a.at:
        snapshots(proj, style, ctx, [float(x) for x in a.at.split(",")], a.safe)
    else:
        full(proj, style, ctx, a.safe, a.draft)


if __name__ == "__main__":
    sys.exit(main())
