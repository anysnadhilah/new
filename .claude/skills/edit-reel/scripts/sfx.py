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


def riser():
    """Rising swell (0.6 s) that peaks at its end: place it so the end lands on the moment."""
    x = t(0.6)
    f = 300 * (1 + 5 * (x / x[-1]) ** 2)
    tone = np.sin(2 * np.pi * np.cumsum(f) / SR) * 0.35
    air = (lowpass(rng.standard_normal(len(x)), 5000) - lowpass(rng.standard_normal(len(x)), 800)) * 0.9
    shape = (x / x[-1]) ** 2.2
    return (tone + air) * shape * np.clip((x[-1] - x) / 0.03, 0, 1)


def impact():
    x = t(0.7)
    f = 95 * np.exp(-x * 6) + 42
    sub = np.sin(2 * np.pi * np.cumsum(f) / SR) * env(len(x), 0.002, 5.5)
    thump = lowpass(rng.standard_normal(len(x)), 900) * env(len(x), 0.001, 30) * 1.2
    return sub + thump


def ding():
    x = t(1.3)
    s = sum(np.sin(2 * np.pi * 1318 * r * x) * env(len(x), 0.002, d) * a
            for r, d, a in ((1, 3.2, 1.0), (2.76, 6, 0.35), (5.4, 11, 0.15)))
    return s


def notify():
    a, b = t(0.09), t(0.14)
    s1 = np.sin(2 * np.pi * 880 * a) * env(len(a), 0.003, 25)
    s2 = np.sin(2 * np.pi * 1320 * b) * env(len(b), 0.003, 18)
    return np.concatenate([s1, np.zeros(int(0.03 * SR)), s2])


def typing():
    out = np.zeros(int(0.9 * SR))
    pos = 0
    while pos < len(out) - 3000:
        k = tick() * rng.uniform(0.4, 0.9)
        out[pos:pos + len(k)] += k[: len(out) - pos]
        pos += int(rng.uniform(0.05, 0.11) * SR)
    return out


def rustle():
    x = t(0.5)
    n = highpass(lowpass(rng.standard_normal(len(x)), 6000), 1200)
    am = np.abs(lowpass(rng.standard_normal(len(x)), 25)) * 6
    return n * am * np.sin(np.pi * x / x[-1]) ** 0.7


def swish():
    x = t(0.24)
    n = highpass(rng.standard_normal(len(x)), 1500)
    return n * np.sin(np.pi * x / x[-1]) ** 3


def chime():
    x = t(1.0)
    s = np.zeros_like(x)
    for i, f in enumerate([1046.5, 1318.5, 1568.0]):
        st = int(i * 0.08 * SR)
        seg = x[: len(x) - st]
        s[st:] += np.sin(2 * np.pi * f * seg) * env(len(seg), 0.004, 4.5) * 0.7
    return s


def boop():
    x = t(0.16)
    f = 420 * np.exp(-x * 9) + 180
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * env(len(x), 0.004, 22)


def swoosh():
    x = t(0.8)
    n = rng.standard_normal(len(x))
    band = lowpass(n, 3200) - lowpass(n, 500)
    return band * np.sin(np.pi * x / x[-1]) ** 1.5 * 1.4


SOUNDS = {"pop": pop, "twinkle": twinkle, "whoosh": whoosh, "slap": slap, "tick": tick, "shutter": shutter,
          "riser": riser, "impact": impact, "ding": ding, "notify": notify, "typing": typing, "rustle": rustle,
          "swish": swish, "chime": chime, "boop": boop, "swoosh": swoosh}


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
