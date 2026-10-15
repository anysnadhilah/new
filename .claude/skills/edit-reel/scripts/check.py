"""QA a finished render: a frame just after every cut (with the safe-area guide) and audio levels.

    check.py <project> <render.mp4>

Writes work/check.jpg. Look at it: every after-cut frame should show the new shot cleanly with no
leftover text from the previous line, nothing on the face, nothing outside the red lines.
"""
import re
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw

from common import FPS, H, W, die, load_json, project_dir
from gfx import font
from styles.base import blank, safe_guides


def main():
    if len(sys.argv) < 3:
        die("usage: check.py <project> <render.mp4>")
    proj = project_dir(sys.argv[1])
    video = Path(sys.argv[2])
    if not video.is_absolute():
        video = proj / video
    tl = load_json(proj / "timeline.json")
    times = [(f"cut {s['id']}", s["start"] + 2 / FPS) for s in tl["segments"]]
    guide = blank()
    safe_guides(guide)
    thumbs = []
    for label, t in times:
        p = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.3f}", "-i", str(video), "-frames:v", "1",
                            "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True)
        if p.returncode or len(p.stdout) < W * H * 3:
            continue
        im = Image.frombytes("RGB", (W, H), p.stdout[: W * H * 3]).convert("RGBA")
        im.alpha_composite(guide)
        thumbs.append((label, t, im.convert("RGB").resize((W // 4, H // 4))))
    cols = 6
    rows = (len(thumbs) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * W // 4, rows * (H // 4 + 26)), "#111")
    d = ImageDraw.Draw(sheet)
    for i, (label, t, im) in enumerate(thumbs):
        x, y = (i % cols) * W // 4, (i // cols) * (H // 4 + 26)
        sheet.paste(im, (x, y + 26))
        d.text((x + 6, y + 3), f"{label} {t:.2f}s", fill="#fff", font=font("Jost-Medium.ttf", 17))
    out = proj / "work" / "check.jpg"
    sheet.save(out, quality=85)

    r = subprocess.run(["ffmpeg", "-v", "info", "-i", str(video), "-af", "volumedetect", "-vn", "-f", "null", "-"],
                       capture_output=True, text=True)
    peak = re.search(r"max_volume: (-?[\d.]+) dB", r.stderr)
    mean = re.search(r"mean_volume: (-?[\d.]+) dB", r.stderr)
    print(f"wrote {out}")
    if peak and mean:
        pk, mn = float(peak.group(1)), float(mean.group(1))
        verdict = "OK" if -6 <= pk <= -0.5 and mn > -24 else "CHECK"
        print(f"audio: peak {pk} dB, mean {mn} dB -> {verdict} (want peak -6..-0.5 dB, mean above -24 dB)")


if __name__ == "__main__":
    sys.exit(main())
