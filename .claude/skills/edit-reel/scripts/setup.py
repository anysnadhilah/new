"""One-time (and every-run) environment check for edit-reel.

Run with any system Python 3.9+. It creates the skill's own virtual environment, installs the
Python packages, downloads the fonts, generates the sound effects and prints STATUS lines.
The last line is READY when everything works.
"""
import json
import platform
import re
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

SK = Path(__file__).resolve().parent.parent
VENV = SK / ".venv"
FONTS = SK / "assets" / "fonts"
PACKAGES = ["faster-whisper", "opencv-python-headless<5", "pillow", "numpy", "gdown", "yt-dlp", "instaloader", "onnxruntime"]

# file name -> Google Fonts css2 family spec (all SIL Open Font License)
FONT_SPECS = {
    "Jost-Medium.ttf": "Jost:wght@500",
    "ShadowsIntoLight-Regular.ttf": "Shadows+Into+Light",
    "Tinos-Regular.ttf": "Tinos",
    "Tinos-Italic.ttf": "Tinos:ital@1",
    "Figtree-ExtraBold.ttf": "Figtree:wght@800",
    "Figtree-Medium.ttf": "Figtree:wght@500",
    "Fraunces-SemiBoldItalic.ttf": "Fraunces:ital,wght@1,600",
    "PlayfairDisplay-SemiBold.ttf": "Playfair+Display:wght@600",
    "Nunito-Black.ttf": "Nunito:wght@900",
    "Fredoka-Bold.ttf": "Fredoka:wght@700",
    "Sacramento-Regular.ttf": "Sacramento",
    "InstrumentSerif-Regular.ttf": "Instrument+Serif",
}

ok = True


def status(name, good, fix=""):
    global ok
    ok = ok and good
    print(f"STATUS {name}: {'OK' if good else 'MISSING'}{'' if good else '  -> ' + fix}")


def venv_python():
    return VENV / ("Scripts/python.exe" if platform.system() == "Windows" else "bin/python")


def main():
    system = platform.system()
    if system == "Windows":
        print("STATUS os: Windows is not supported yet (macOS and Linux only in this version).")
        sys.exit(1)

    status("python", sys.version_info >= (3, 9), "install Python 3.9 or newer (Mac: brew install python)")
    brew = "brew install ffmpeg" if system == "Darwin" else "sudo apt install ffmpeg"
    status("ffmpeg", bool(shutil.which("ffmpeg") and shutil.which("ffprobe")), brew)
    if not ok:
        sys.exit(1)

    py = venv_python()
    if not py.exists():
        r = subprocess.run([sys.executable, "-m", "venv", str(VENV)], capture_output=True, text=True)
        if r.returncode != 0:
            status("venv", False, "Linux: sudo apt install python3-venv")
            sys.exit(1)
    check = "import faster_whisper, cv2, PIL, numpy, gdown, yt_dlp, instaloader, onnxruntime"
    if subprocess.run([str(py), "-c", check], capture_output=True).returncode != 0:
        print("installing Python packages (first run takes a minute)...", flush=True)
        subprocess.run([str(py), "-m", "pip", "install", "-q", "--upgrade", "pip"], capture_output=True)
        r = subprocess.run([str(py), "-m", "pip", "install", "-q", *PACKAGES], capture_output=True, text=True)
        if r.returncode != 0:
            print(r.stderr[-1500:])
    status("python packages", subprocess.run([str(py), "-c", check], capture_output=True).returncode == 0,
           f"{py} -m pip install {' '.join(PACKAGES)}")

    FONTS.mkdir(parents=True, exist_ok=True)
    missing = []
    for fname, spec in FONT_SPECS.items():
        dest = FONTS / fname
        if dest.exists() and dest.stat().st_size > 10000:
            continue
        try:
            css = urllib.request.urlopen(f"https://fonts.googleapis.com/css2?family={spec}", timeout=30).read().decode()
            url = re.search(r"url\((https://[^)]+\.ttf)\)", css).group(1)
            dest.write_bytes(urllib.request.urlopen(url, timeout=60).read())
        except Exception as e:  # offline or blocked
            missing.append(f"{fname} ({e.__class__.__name__})")
    status("fonts", not missing, "needs internet once to download: " + ", ".join(missing))

    r = subprocess.run([str(py), str(SK / "scripts" / "sfx.py")], capture_output=True, text=True)
    status("sound effects", r.returncode == 0, r.stderr[-500:])

    (SK / ".platform.json").write_text(json.dumps({
        "os": {"Darwin": "macos"}.get(system, system.lower()),
        "machine": platform.machine(),
        "python": str(py),
    }, indent=2))
    print("READY" if ok else "NOT READY: fix the MISSING lines above, then run setup again")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
