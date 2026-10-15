"""Synthesises the skill's sound effects from scratch (no third-party samples, nothing to license).

Writes 48 kHz mono WAVs into assets/sfx/. Run by setup.py; safe to re-run.
"""
import wave
from pathlib import Path

import numpy as np

SR = 48000
OUT = Path(__file__).resolve().parent.parent / "assets" / "sfx"
rng = np.random.default_rng(7)


def t(sec):
    return np.arange(int(SR * sec)) / SR


def env(n, attack=0.004, decay=8.0):
    x = np.arange(n) / SR
    a = np.clip(x / attack, 0, 1)
    return a * np.exp(-x * decay)


def lowpass(x, cutoff):
    # one-pole low-pass, good enough for soft textures
    a = np.exp(-2 * np.pi * cutoff / SR)
    y = np.empty_like(x)
    acc = 0.0
    for i, v in enumerate(x):
        acc = (1 - a) * v + a * acc
        y[i] = acc
    return y


def highpass(x, cutoff):
    return x - lowpass(x, cutoff)


def pop():
    x = t(0.12)
    f = 900 * np.exp(-x * 28) + 260          # quick downward pitch bend
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * env(len(x), 0.002, 38)
    return s


def twinkle():
    x = t(0.9)
    s = np.zeros_like(x)
    for i, f in enumerate([2093, 2637, 3136, 4186]):        # C7 E7 G7 C8 arpeggio
        start = int(i * 0.06 * SR)
        seg = x[: len(x) - start]
        s[start:] += np.sin(2 * np.pi * f * seg) * env(len(seg), 0.003, 6.5) * (0.9 - i * 0.15)
    return s * 0.6


def whoosh():
    x = t(0.45)
    n = rng.standard_normal(len(x))
    shape = np.sin(np.pi * x / x[-1]) ** 2
    lo = lowpass(n, 2400) - lowpass(n, 300)
    return lo * shape * 1.6


def slap():
    x = t(0.18)
    n = rng.standard_normal(len(x))
    body = lowpass(n, 1800) * env(len(x), 0.001, 30)
    crinkle = highpass(rng.standard_normal(len(x)), 3000) * env(len(x), 0.001, 55) * 0.35
    return body * 1.4 + crinkle


def tick():
    x = t(0.05)
    n = highpass(rng.standard_normal(len(x)), 2500)
    return n * env(len(x), 0.0005, 120) * 0.8 + np.sin(2 * np.pi * 1800 * x) * env(len(x), 0.0005, 160) * 0.3


def shutter():
    a = tick()
    gap = np.zeros(int(0.07 * SR))
    return np.concatenate([a, gap, a * 0.7])


SOUNDS = {"pop": pop, "twinkle": twinkle, "whoosh": whoosh, "slap": slap, "tick": tick, "shutter": shutter}


def write(name, s):
    s = s / (np.max(np.abs(s)) + 1e-9) * 0.7          # peak -3 dBFS; mixing gain is applied at render
    pcm = (s * 32767).astype("<i2")
    with wave.open(str(OUT / f"{name}.wav"), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    for name, fn in SOUNDS.items():
        write(name, fn())
    print(f"wrote {len(SOUNDS)} sounds to {OUT}")
