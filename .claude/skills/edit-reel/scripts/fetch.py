"""Bring raw clips into a project.

    fetch.py <project> <source> [<source> ...] [--newest N]

A source is a video file, a folder of videos, or a link:
  - Google Drive file or folder (shared as "Anyone with the link")
  - Dropbox share link
  - a direct link to a video file (https://.../video.mp4)
  - YouTube / Instagram / TikTok and other video pages (the user's own content), through yt-dlp
Local files are linked, never moved or changed. Downloads go into <project>/clips/.
"""
import argparse
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

from common import VIDEO_EXT, die, project_dir

START = time.time() - 1


def from_drive(url, dest):
    import gdown
    dest.mkdir(parents=True, exist_ok=True)
    if "/folders/" in url:
        got = gdown.download_folder(url=url, output=str(dest), quiet=True, remaining_ok=True)
    else:
        got = [gdown.download(url=url, output=str(dest) + os.sep, quiet=True, fuzzy=True)]
    got = [g for g in (got or []) if g]
    if not got:
        die("Google Drive download failed. Is the link shared as 'Anyone with the link'?")
    return [Path(g) for g in got]


def from_url(url, dest):
    """Plain download of a video file link (Dropbox, direct links)."""
    name = Path(urllib.parse.urlparse(url).path).name or "video.mp4"
    if Path(name).suffix.lower() not in VIDEO_EXT:
        name += ".mp4"
    target = dest / name
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as r, open(target, "wb") as f:
        shutil.copyfileobj(r, f)
    if target.stat().st_size < 50_000:
        target.unlink()
        die(f"that link did not give a video file: {url}")
    return [target]


def from_page(url, dest):
    """Video pages (YouTube, Instagram, TikTok...) through yt-dlp. Only for the user's own videos."""
    out = dest / "%(title).60s-%(id)s.%(ext)s"
    r = subprocess.run([str(Path(sys.executable).parent / "yt-dlp"), "-q", "--no-warnings", "--no-playlist",
                        "-f", "bv*[height<=2160]+ba/b", "--merge-output-format", "mp4", "-o", str(out), url],
                       capture_output=True, text=True)
    files = [f for f in dest.iterdir() if f.suffix.lower() in VIDEO_EXT and f.stat().st_mtime > START]
    if r.returncode != 0 or not files:
        die(f"could not download {url} ({(r.stderr or '').strip()[-200:]}). Ask the user to share it through "
            f"Google Drive instead.")
    return files


def link_local(path, dest, newest):
    p = Path(os.path.expanduser(path)).resolve()
    if not p.exists():
        die(f"not found: {p}")
    files = [p] if p.is_file() else [f for f in p.iterdir() if f.suffix.lower() in VIDEO_EXT and not f.name.startswith(".")]
    if p.is_dir():
        files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
        files = sorted(files[:newest] if newest else files)
    out = []
    for f in files:
        target = dest / f.name
        if not target.exists():
            try:
                target.symlink_to(f)
            except OSError:
                shutil.copy2(f, target)
        out.append(target)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("project")
    ap.add_argument("sources", nargs="+")
    ap.add_argument("--newest", type=int, default=0, help="from a folder, only the N most recent videos")
    a = ap.parse_args()
    proj = project_dir(a.project)
    dest = proj / "clips"
    dest.mkdir(exist_ok=True)
    got = []
    for s in a.sources:
        if s.startswith("http"):
            if "drive.google.com" in s:
                got += from_drive(s, dest)
            elif "dropbox.com" in s:
                got += from_url(re.sub(r"([?&])dl=0", r"\1dl=1", s if "dl=" in s else s + ("&" if "?" in s else "?") + "dl=1"), dest)
            elif Path(urllib.parse.urlparse(s).path).suffix.lower() in VIDEO_EXT:
                got += from_url(s, dest)
            else:
                got += from_page(s, dest)
        else:
            got += link_local(s, dest, a.newest)
    videos = [g for g in got if g.suffix.lower() in VIDEO_EXT]
    if not videos:
        die("no video files found in the sources")
    for v in videos:
        print(f"clip: {v.name}")
    print(f"{len(videos)} clip(s) in {dest}")


if __name__ == "__main__":
    sys.exit(main())
