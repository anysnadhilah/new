"""Shared paths, constants and small helpers for every edit-reel script."""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

SK = Path(__file__).resolve().parent.parent          # the skill folder
FONTS = SK / "assets" / "fonts"
SFX = SK / "assets" / "sfx"

W, H, FPS = 1080, 1920, 30
SR = 48000                                            # audio sample rate everywhere

# Instagram Reels safe area (pixels on the 1080x1920 frame). Nothing important outside it.
SAFE = {
    "top": 250,          # profile row / "Reels" header above this
    "bottom": 1440,      # caption, audio row and buttons below this
    "left": 60,
    "right": W - 60,
    "right_low": W - 150,   # like/comment/share column
    "right_low_from": 1100,
}

VIDEO_EXT = {".mp4", ".mov", ".m4v", ".mkv", ".webm", ".avi"}


def die(msg):
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def run(cmd, quiet=True, **kw):
    """Run a command list; raise with stderr on failure."""
    r = subprocess.run([str(c) for c in cmd], capture_output=quiet, text=True, **kw)
    if r.returncode != 0:
        err = (r.stderr or "")[-2000:] if quiet else ""
        raise RuntimeError(f"command failed ({r.returncode}): {' '.join(map(str, cmd[:6]))} ...\n{err}")
    return r


def ffprobe(path):
    r = run(["ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams", path])
    info = json.loads(r.stdout)
    v = next((s for s in info["streams"] if s["codec_type"] == "video"), None)
    if v is None:
        raise RuntimeError(f"no video stream in {path}")
    w, h = int(v["width"]), int(v["height"])
    rot = 0
    for sd in v.get("side_data_list", []) or []:
        if "rotation" in sd:
            rot = int(sd["rotation"])
    rot = int(v.get("tags", {}).get("rotate", rot))
    if abs(rot) % 180 == 90:
        w, h = h, w
    num, den = (v.get("avg_frame_rate") or "30/1").split("/")
    fps = float(num) / float(den or 1) if float(den or 1) else 30.0
    return {
        "width": w, "height": h, "fps": round(fps, 3),
        "duration": float(info["format"].get("duration") or v.get("duration") or 0),
        "has_audio": any(s["codec_type"] == "audio" for s in info["streams"]),
    }


def load_json(path, default=None):
    p = Path(path)
    if not p.exists():
        if default is not None:
            return default
        die(f"missing {p}")
    return json.loads(p.read_text())


def save_json(path, data):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(data, indent=2, ensure_ascii=False))


def project_dir(arg):
    p = Path(os.path.expanduser(arg)).resolve()
    p.mkdir(parents=True, exist_ok=True)
    (p / "work").mkdir(exist_ok=True)
    (p / "renders").mkdir(exist_ok=True)
    return p


def config():
    return load_json(SK / "config.json", default={})


def have(tool):
    return shutil.which(tool) is not None
