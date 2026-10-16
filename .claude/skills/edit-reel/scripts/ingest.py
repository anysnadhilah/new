"""Probe, transcribe and face-track every clip in <project>/clips.

    ingest.py <project> [--model small] [--language en]

Writes:
  transcript.json  clips -> {file, duration, language, words[{w,s,e}], lines[{s,e,text}], faces[[t,cx,cy,w,h]]}
  transcript.txt   readable per-clip lines with times and pauses, for picking takes
  work/sheet.jpg   three frames per clip, to see setups and framing
"""
import argparse
import re
import subprocess
import sys
import time

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from common import FONTS, VIDEO_EXT, config, die, ffprobe, project_dir, save_json

SAMPLE_FPS = 1
SW, SH = 270, 480          # face-sampling frame size


def decode(src, work, cid, info):
    """16 kHz mono wav for Whisper + small frames for faces and the contact sheet.

    Frames come from keyframes only (phones write one about every second), which is many times faster
    than decoding every frame of 4K HEVC."""
    wav = work / f"{cid}.wav"
    if info["has_audio"]:
        p = subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-vn", "-map", "0:a:0", "-ac", "1",
                            "-ar", "16000", str(wav)], capture_output=True)
    else:                                   # silent video: a silent track keeps every later step the same
        p = subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "anullsrc=r=16000:cl=mono",
                            "-t", f"{info['duration']:.3f}", str(wav)], capture_output=True)
    if p.returncode != 0:
        die(f"ffmpeg could not read the audio of {src.name}: {p.stderr.decode()[-800:]}")
    cmd = ["ffmpeg", "-v", "error", "-skip_frame", "nokey", "-i", str(src), "-an", "-map", "0:v:0",
           "-vf", f"fps={SAMPLE_FPS},scale={SW}:{SH}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
    p = subprocess.run(cmd, capture_output=True)
    if p.returncode != 0:
        die(f"ffmpeg could not decode {src.name}: {p.stderr.decode()[-800:]}")
    frames = np.frombuffer(p.stdout, np.uint8)
    frames = frames[: len(frames) // (SW * SH * 3) * SW * SH * 3].reshape(-1, SH, SW, 3)
    if len(frames) < max(2, info["duration"] * SAMPLE_FPS * 0.5):
        # few keyframes in this file: decode every frame instead (slower, always works)
        p = subprocess.run([a for a in cmd if a not in ("-skip_frame", "nokey")], capture_output=True)
        frames = np.frombuffer(p.stdout, np.uint8)
        frames = frames[: len(frames) // (SW * SH * 3) * SW * SH * 3].reshape(-1, SH, SW, 3)
    return wav, frames


def faces(frames):
    import cv2
    det = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    out = []
    for i, f in enumerate(frames):
        g = cv2.cvtColor(f, cv2.COLOR_RGB2GRAY)
        found = det.detectMultiScale(g, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
        if len(found):
            x, y, w, h = max(found, key=lambda b: b[2] * b[3])
            out.append([round(i / SAMPLE_FPS, 2), round((x + w / 2) / SW, 4), round((y + h / 2) / SH, 4),
                        round(w / SW, 4), round(h / SH, 4)])
    return out


def transcribe(model, wav, language, prompt):
    import wave
    with wave.open(str(wav)) as f:
        audio = np.frombuffer(f.readframes(f.getnframes()), "<i2").astype(np.float32) / 32768
    segs, info = model.transcribe(audio, language=language, word_timestamps=True, vad_filter=False,
                                  initial_prompt=prompt or None, condition_on_previous_text=False)
    words, lines = [], []
    for s in segs:
        # music, noise and silence make Whisper invent text: keep only what is really speech
        if (s.no_speech_prob > 0.6 and s.avg_logprob < -0.7) or not re.search(r"\w{2,}", s.text):
            continue
        kept = [w for w in s.words or [] if re.search(r"[^\W_]", w.word) and w.probability > 0.15]
        if not kept:
            continue
        lines.append({"s": round(s.start, 2), "e": round(s.end, 2), "text": s.text.strip()})
        for w in kept:
            words.append({"w": w.word.strip(), "s": round(w.start, 3), "e": round(w.end, 3)})
    return words, lines, info.language


def readable(cid, c):
    out = [f"=== {cid}  {c['file']}  ({c['duration']:.1f}s, {c['language']})"]
    prev = 0.0
    for ln in c["lines"]:
        if ln["s"] - prev >= 0.6:
            out.append(f"   (pause {ln['s'] - prev:.1f}s)")
        out.append(f"[{ln['s']:6.2f} - {ln['e']:6.2f}] {ln['text']}")
        prev = ln["e"]
    return "\n".join(out)


def sheet(proj, thumbs):
    cols = 3
    tw, th = SW, SH
    img = Image.new("RGB", (cols * tw, len(thumbs) * (th + 28)), "#111")
    d = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype(str(FONTS / "Jost-Medium.ttf"), 20)
    except OSError:
        font = ImageFont.load_default()
    for r, (cid, frames) in enumerate(thumbs):
        for c, (t, f) in enumerate(frames):
            img.paste(Image.fromarray(f), (c * tw, r * (th + 28) + 28))
            d.text((c * tw + 8, r * (th + 28) + 3), f"{cid} @ {t:.1f}s", fill="#fff", font=font)
    img.save(proj / "work" / "sheet.jpg", quality=85)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("project")
    ap.add_argument("--model", default=config().get("whisperModel", "small"))
    ap.add_argument("--language", default=config().get("language") or None, help="e.g. en, ms; default auto-detect")
    ap.add_argument("--prompt", default="", help="names and keywords that appear in the video")
    a = ap.parse_args()
    proj = project_dir(a.project)
    clips = sorted(f for f in (proj / "clips").iterdir() if f.suffix.lower() in VIDEO_EXT) if (proj / "clips").exists() else []
    if not clips:
        die(f"no clips in {proj / 'clips'}; run fetch.py first")

    from faster_whisper import WhisperModel
    model = WhisperModel(a.model, device="auto", compute_type="int8")

    data, thumbs, txt = {}, [], []
    for i, src in enumerate(clips, 1):
        cid = f"c{i}"
        t0 = time.time()
        info = ffprobe(src)
        wav, frames = decode(src, proj / "work", cid, info)
        words, lines, lang = transcribe(model, wav, a.language, a.prompt)
        c = {"file": src.name, "duration": round(info["duration"], 3), "width": info["width"],
             "height": info["height"], "fps": info["fps"], "language": lang,
             "words": words, "lines": lines, "faces": faces(frames)}
        data[cid] = c
        n = len(frames)
        thumbs.append((cid, [(j / SAMPLE_FPS, frames[j]) for j in (int(n * .1), n // 2, int(n * .9)) if n]))
        txt.append(readable(cid, c))
        print(f"{cid}: {src.name} {info['duration']:.1f}s, {len(words)} words, "
              f"face in {len(c['faces'])}/{n} samples ({time.time() - t0:.0f}s)", flush=True)

    save_json(proj / "transcript.json", {"clips": data})
    (proj / "transcript.txt").write_text("\n\n".join(txt) + "\n")
    sheet(proj, thumbs)
    print(f"wrote {proj / 'transcript.txt'} and {proj / 'work' / 'sheet.jpg'}")


if __name__ == "__main__":
    sys.exit(main())
