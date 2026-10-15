"""Effect base class, cutout (matte) access and shared helpers.

An effect lives in plan.json "effects": {"type": "...", "start": 4.2, "end": 7.0, ...options}.
Per frame, render.py calls compose(): background work (needs the cutout), the person on top, whole-frame
transforms, then overlays in front. The style's captions are drawn after that.
"""
import json

import cv2
import numpy as np
from PIL import Image, ImageFilter

from common import FPS, H, W
from gfx import clamp01, out_cubic, prog


class Matte:
    """Reads the cutout written by cutout.py; returns a full-size 'L' image or None for frames without one."""

    def __init__(self, work):
        self.rows, self.store = {}, None
        idx = work / "matte.json"
        if idx.exists() and (work / "matte.npy").exists():
            frames = json.loads(idx.read_text()).get("frames", [])
            self.rows = {f: i for i, f in enumerate(frames)}
            if frames:
                self.store = np.load(work / "matte.npy", mmap_mode="r")
        self.cache = (None, None)

    def at(self, frame):
        if self.cache[0] == frame:
            return self.cache[1]
        row = self.rows.get(frame)
        img = None
        if row is not None:
            m = cv2.resize(np.asarray(self.store[row]), (W, H), interpolation=cv2.INTER_LINEAR)
            img = Image.fromarray(m, "L")
        self.cache = (frame, img)
        return img


class Effect:
    name = "effect"
    needs_matte = False
    hides_captions = False
    reserves = None          # "top" / "bottom": captions move to the other zone while this effect shows
    ease_in = 0.35
    ease_out = 0.3

    def __init__(self, spec, ctx):
        self.s = spec
        self.ctx = ctx
        self.start = float(spec.get("start", 0))
        self.end = float(spec.get("end", self.start + 2.5))

    def active(self, t):
        return self.start <= t < self.end

    def env(self, t):
        """0 → 1 → 0 envelope for the in/out animation."""
        return out_cubic(prog(t, self.start, self.ease_in)) * (1 - out_cubic(prog(t, self.end - self.ease_out, self.ease_out)))

    def local(self, t):
        return t - self.start

    # stages (override what you need) --------------------------------------------------------
    def background(self, bg, t):            # RGB image without the person on top yet; return new RGB
        return bg

    def behind(self, bg, t):                # draw onto the background (RGB) behind the person
        pass

    def person(self, person, matte, t):     # RGBA cut-out of the speaker; return new RGBA
        return person

    def whole(self, frame, t):              # whole-frame transform after the person is back; return RGB
        return frame

    def front(self, frame, t):              # overlays in front of everything (before captions)
        pass

    # helpers ------------------------------------------------------------------------------------
    def face(self, t):
        """(cx, cy, head_top, chin) in pixels for the shot at t; sensible defaults without a face."""
        seg = self.ctx.seg_at(t)
        f = seg.get("face")
        if not f:
            return W / 2, H * 0.4, H * 0.25, H * 0.55
        box = self.ctx.face_px(seg)
        return f["cx"] * W, f["cy"] * H, box[1], box[3]


# ---------------------------------------------------------------- image helpers
def zoom(img, z, cx=W / 2, cy=H / 2):
    """Zoom an RGB frame by z around (cx, cy), keeping the frame size."""
    if abs(z - 1) < 1e-3:
        return img
    a = np.asarray(img)
    m = np.float32([[z, 0, cx - z * cx], [0, z, cy - z * cy]])
    out = cv2.warpAffine(a, m, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    return Image.fromarray(out)


def zoom_blur(img, z, strength, cx=W / 2, cy=H / 2):
    """Radial zoom blur: average of a few progressively zoomed copies."""
    a = np.asarray(zoom(img, z, cx, cy)).astype(np.float32)
    acc, n = a.copy(), 1
    for k in (1.03, 1.06, 1.1)[: max(1, int(strength * 3))]:
        acc += np.asarray(zoom(img, z * k, cx, cy)).astype(np.float32)
        n += 1
    return Image.fromarray((acc / n).astype(np.uint8))


def fast_blur(img, radius):
    small = img.resize((W // 6, H // 6), Image.BILINEAR).filter(ImageFilter.GaussianBlur(radius / 6))
    return small.resize((W, H), Image.BILINEAR)


def rounded(img, radius):
    mask = Image.new("L", img.size, 0)
    from PIL import ImageDraw
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, img.width - 1, img.height - 1), radius=radius, fill=255)
    out = img.convert("RGBA")
    out.putalpha(mask)
    return out


def cover(img, w=W, h=H):
    """Resize + centre-crop an image to fill w x h."""
    k = max(w / img.width, h / img.height)
    img = img.resize((int(img.width * k + 1), int(img.height * k + 1)), Image.LANCZOS)
    x, y = (img.width - w) // 2, (img.height - h) // 2
    return img.crop((x, y, x + w, y + h))


def clips_thumbs(ctx, n, size=(170, 300)):
    """n stills from across the reel itself (for orbits and drop zones when the user gives no images)."""
    import subprocess
    out = []
    if not getattr(ctx, "project", None):
        return out
    src = ctx.project / "work" / "aroll.mkv"
    for i in range(n):
        t = ctx.duration * (i + 0.5) / n
        p = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.2f}", "-i", str(src), "-frames:v", "1",
                            "-vf", f"scale={size[0]}:{size[1]}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                           capture_output=True)
        if len(p.stdout) == size[0] * size[1] * 3:
            out.append(Image.frombytes("RGB", size, p.stdout))
    return out


def user_image(ctx, path):
    from pathlib import Path
    p = Path(path)
    if not p.is_absolute() and getattr(ctx, "project", None):
        p = ctx.project / p
    return Image.open(p).convert("RGB")


def frame_index(t):
    return int(round(t * FPS))


__all__ = ["Effect", "Matte", "zoom", "zoom_blur", "fast_blur", "rounded", "cover", "clips_thumbs", "user_image",
           "clamp01"]
