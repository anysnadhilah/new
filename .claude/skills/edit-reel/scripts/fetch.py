"""Bring raw clips into a project.

    fetch.py <project> <source> [<source> ...] [--newest N]

A source is a video file, a folder of videos, or a Google Drive share link (file or folder,
shared as "anyone with the link"). Local files are linked, never moved or changed.
Drive files are downloaded into <project>/clips/.
"""
import argparse
import os
import sys
from pathlib import Path

from common import VIDEO_EXT, die, project_dir


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
                import shutil
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
            if "drive.google.com" not in s:
                die(f"only Google Drive links are supported: {s}")
            got += from_drive(s, dest)
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
