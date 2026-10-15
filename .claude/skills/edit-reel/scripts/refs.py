"""Download style references (YouTube / Instagram / Drive links or local files) and make contact sheets to study.

    refs.py <project> <link or file> [<link or file> ...]

Writes <project>/refs/ref<N>.* and refs/ref<N>-sheet.jpg (12 frames of a video, or the images of a photo post).
Instagram often blocks anonymous downloads; if a link fails, ask the user to save the reel to their phone and
share it through Google Drive instead.
"""
import glob
import re
import subprocess
import sys
from pathlib import Path

from PIL import Image

from common import VIDEO_EXT, project_dir

BIN = Path(sys.executable).parent


def download(link, dest, n):
    if Path(link).exists():
        return [Path(link)]
    if "drive.google.com" in link:
        import gdown
        got = gdown.download(url=link, output=str(dest) + "/", quiet=True, fuzzy=True)
        return [Path(got)] if got else []
    r = subprocess.run([str(BIN / "yt-dlp"), "-q", "--no-warnings", "--no-playlist", "-o",
                        str(dest / f"ref{n}.%(ext)s"), link], capture_output=True, text=True)
    files = sorted(glob.glob(str(dest / f"ref{n}.*")))
    if files:
        return [Path(f) for f in files]
    m = re.search(r"instagram\.com/(?:p|reel)/([\w-]+)", link)
    if m:                                     # photo posts (carousels) are not videos: fetch the images
        sub = dest / f"ref{n}-post"
        subprocess.run([str(BIN / "instaloader"), "--no-videos", "--no-metadata-json", "--no-captions", "--quiet",
                        f"--dirname-pattern={sub}", "--", f"-{m.group(1)}"], capture_output=True, text=True)
        return sorted(Path(f) for f in glob.glob(str(sub / "*.jpg")))
    print(f"could not download {link}: {r.stderr.strip()[-300:]}")
    return []


def sheet(files, out):
    vids = [f for f in files if f.suffix.lower() in VIDEO_EXT]
    if vids:
        d = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                                  str(vids[0])], capture_output=True, text=True).stdout or 10)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(vids[0]), "-vf",
                        f"fps=12/{d:.2f},scale=270:-2,tile=6x2", "-frames:v", "1", str(out)], check=True)
        return True
    imgs = [Image.open(f).convert("RGB") for f in files[:6]]
    if not imgs:
        return False
    imgs = [i.resize((324, int(i.height * 324 / i.width))) for i in imgs]
    s = Image.new("RGB", (324 * len(imgs), max(i.height for i in imgs)), "white")
    for k, i in enumerate(imgs):
        s.paste(i, (324 * k, 0))
    s.save(out, quality=90)
    return True


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return 1
    proj = project_dir(sys.argv[1])
    dest = proj / "refs"
    dest.mkdir(exist_ok=True)
    for n, link in enumerate(sys.argv[2:], 1):
        files = download(link, dest, n)
        out = dest / f"ref{n}-sheet.jpg"
        print(f"ref{n}: {'sheet ' + str(out) if files and sheet(files, out) else 'FAILED (ask for a Drive copy)'}")


if __name__ == "__main__":
    sys.exit(main())
