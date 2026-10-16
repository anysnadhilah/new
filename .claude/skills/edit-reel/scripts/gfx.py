"""Drawing toolkit for the styles: text, shapes, transforms and easing. Pure Pillow + numpy.

Everything is drawn procedurally (no stock art), so every graphic in a reel is original.
"""
import math
from functools import lru_cache

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from common import FONTS


# ------------------------------------------------------------------ easing
def clamp01(x):
    return 0.0 if x < 0 else 1.0 if x > 1 else x


def prog(t, start, dur):
    """0..1 progress of an animation that starts at `start` and lasts `dur` seconds."""
    return clamp01((t - start) / dur) if dur > 0 else float(t >= start)


def out_cubic(x):
    return 1 - (1 - x) ** 3


def out_expo(x):
    return 1.0 if x >= 1 else 1 - 2 ** (-10 * x)


def out_back(x, k=1.9):
    x -= 1
    return 1 + (k + 1) * x ** 3 + k * x ** 2


def in_out_sine(x):
    return -(math.cos(math.pi * x) - 1) / 2


def lerp(a, b, x):
    return a + (b - a) * x


# ------------------------------------------------------------------ colour
def rgba(hex_or_tuple, alpha=255):
    if isinstance(hex_or_tuple, tuple):
        return hex_or_tuple if len(hex_or_tuple) == 4 else (*hex_or_tuple, alpha)
    from PIL import ImageColor
    return ImageColor.getrgb(hex_or_tuple)[:3] + (alpha,)


# ------------------------------------------------------------------ text
@lru_cache(maxsize=64)
def font(name, size):
    return ImageFont.truetype(str(FONTS / name), int(size))


def text_img(text, font_name, size, fill="#ffffff", stroke=0, stroke_fill=None, tracking=0.0,
             shadow=None, pad=None):
    """Render text tightly into an RGBA image.

    tracking: extra space between letters in em (0.2 = 20% of the size).
    shadow:   (dx, dy, blur, colour) drawn under the text.
    """
    f = font(font_name, size)
    track = tracking * size
    advances = [f.getlength(ch) + track for ch in text]
    width = sum(advances) - (track if text else 0)
    asc, desc = f.getmetrics()
    sh_pad = 0 if shadow is None else int(abs(shadow[0]) + abs(shadow[1]) + shadow[2] * 2.5)
    p = pad if pad is not None else stroke + 4 + sh_pad
    w, h = int(math.ceil(width)) + 2 * p, asc + desc + 2 * p
    img = Image.new("RGBA", (max(w, 1), max(h, 1)), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    x = p
    for ch, adv in zip(text, advances):
        d.text((x, p), ch, font=f, fill=rgba(fill), stroke_width=stroke,
               stroke_fill=rgba(stroke_fill) if stroke_fill else None)
        x += adv
    if shadow:
        dx, dy, blur, col = shadow
        a = img.getchannel("A")
        sh = Image.new("RGBA", img.size, rgba(col)[:3] + (0,))
        sh.putalpha(a.point(lambda v, k=rgba(col)[3] / 255: int(v * k)))
        sh = sh.filter(ImageFilter.GaussianBlur(blur)) if blur else sh
        base = Image.new("RGBA", img.size, (0, 0, 0, 0))
        base.alpha_composite(sh, (int(dx), int(dy)))
        base.alpha_composite(img)
        img = base
    img.info["pad"] = p
    return img


def trim(img):
    box = img.getchannel("A").getbbox()
    return img.crop(box) if box else img


# ------------------------------------------------------------------ transforms and compositing
def xform(img, scale=1.0, rot=0.0, alpha=1.0, blur=0.0, sx=None, sy=None):
    if alpha <= 0.003 or scale <= 0.01:
        return None
    sx = scale if sx is None else sx * scale
    sy = scale if sy is None else sy * scale
    if abs(sx - 1) > 1e-3 or abs(sy - 1) > 1e-3:
        img = img.resize((max(1, int(img.width * sx)), max(1, int(img.height * sy))), Image.BICUBIC)
    if abs(rot) > 0.05:
        img = img.rotate(rot, resample=Image.BICUBIC, expand=True)
    if blur > 0.3:
        b = int(blur * 2) + 2
        canvas = Image.new("RGBA", (img.width + 2 * b, img.height + 2 * b), (0, 0, 0, 0))
        canvas.paste(img, (b, b))
        img = canvas.filter(ImageFilter.GaussianBlur(blur))
    if alpha < 0.997:
        img = img.copy()
        img.putalpha(img.getchannel("A").point(lambda v, k=alpha: int(v * k)))
    return img


def place(canvas, img, cx, cy):
    """Alpha-composite img centred at (cx, cy); safely clips at the canvas edges."""
    if img is None:
        return
    x, y = int(round(cx - img.width / 2)), int(round(cy - img.height / 2))
    put(canvas, img, x, y)


def put(canvas, img, x, y):
    if img is None:
        return
    W, H = canvas.size
    sx0, sy0 = max(0, -x), max(0, -y)
    sx1, sy1 = min(img.width, W - x), min(img.height, H - y)
    if sx1 <= sx0 or sy1 <= sy0:
        return
    if (sx0, sy0, sx1, sy1) != (0, 0, img.width, img.height):
        img = img.crop((sx0, sy0, sx1, sy1))
    canvas.alpha_composite(img, (x + sx0, y + sy0))


def supersample(w, h, draw_fn, k=3):
    """Draw at k x size then downsample, for smooth anti-aliased shapes."""
    big = Image.new("RGBA", (int(w * k), int(h * k)), (0, 0, 0, 0))
    draw_fn(ImageDraw.Draw(big), k)
    return big.resize((int(w), int(h)), Image.LANCZOS)


def drop_shadow(img, dx=0, dy=8, blur=10, color=(0, 0, 0, 110)):
    pad = int(blur * 2.5 + max(abs(dx), abs(dy)))
    base = Image.new("RGBA", (img.width + 2 * pad, img.height + 2 * pad), (0, 0, 0, 0))
    sh = Image.new("RGBA", img.size, color[:3] + (0,))
    sh.putalpha(img.getchannel("A").point(lambda v, k=color[3] / 255: int(v * k)))
    base.alpha_composite(sh, (pad + dx, pad + dy))
    base = base.filter(ImageFilter.GaussianBlur(blur))
    base.alpha_composite(img, (pad, pad))
    return base


def glow(img, blur=12, strength=1.0):
    g = img.filter(ImageFilter.GaussianBlur(blur))
    base = Image.new("RGBA", img.size, (0, 0, 0, 0))
    for _ in range(int(strength)):
        base.alpha_composite(g)
    base.alpha_composite(img)
    return base


# ------------------------------------------------------------------ shapes
def sparkle(size, color="#ffffff", glow_blur=None):
    """Four-point twinkle star (astroid curve) with a soft glow."""
    pad = size // 2

    def draw(d, k):
        c = (size / 2 + pad) * k
        r = size / 2 * k
        pts = []
        for i in range(120):
            a = 2 * math.pi * i / 120
            ca, sa = math.cos(a), math.sin(a)
            pts.append((c + r * math.copysign(abs(ca) ** 3, ca), c + r * math.copysign(abs(sa) ** 3, sa)))
        d.polygon(pts, fill=rgba(color))
    img = supersample(size + 2 * pad, size + 2 * pad, draw)
    return glow(img, glow_blur or max(2, size // 6), 2)


def heart(size, color="#ff8fc1", outline=None, outline_w=0):
    pad = outline_w + 2

    def pts(k, grow=0):
        out = []
        for i in range(100):
            t = 2 * math.pi * i / 100
            x = 16 * math.sin(t) ** 3
            y = -(13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t))
            s = (size / 2 + grow) / 17
            out.append(((size / 2 + pad + x * s) * k, (size / 2 + pad + y * s + size * 0.04) * k))
        return out

    def draw(d, k):
        if outline:
            d.polygon(pts(k, outline_w), fill=rgba(outline))
        d.polygon(pts(k), fill=rgba(color))
    return supersample(size + 2 * pad, size + 2 * pad, draw)


def star5(size, color="#f4cf4a", outline=None, outline_w=0, inner=0.45):
    pad = outline_w + 2

    def pts(k, grow=0):
        c = size / 2 + pad
        out = []
        for i in range(10):
            r = (size / 2 + grow) * (1 if i % 2 == 0 else inner)
            a = -math.pi / 2 + i * math.pi / 5
            out.append(((c + r * math.cos(a)) * k, (c + r * math.sin(a)) * k))
        return out

    def draw(d, k):
        if outline:
            d.polygon(pts(k, outline_w * 1.6), fill=rgba(outline))
        d.polygon(pts(k), fill=rgba(color))
    return supersample(size + 2 * pad + outline_w * 2, size + 2 * pad + outline_w * 2, draw)


def ring(radius, width=3, color=(255, 255, 255, 140)):
    s = radius * 2 + width * 2 + 4

    def draw(d, k):
        o = (width + 2) * k
        d.ellipse((o, o, (s - width - 2) * k, (s - width - 2) * k), outline=rgba(color), width=int(width * k))
    return supersample(s, s, draw)


def jagged_poly(w, h, rng, step=(7, 13), amp=3.0, x0=0, y0=0):
    """Rectangle outline with torn, jittery edges."""
    pts = []
    for (ax, ay, bx, by) in ((0, 0, w, 0), (w, 0, w, h), (w, h, 0, h), (0, h, 0, 0)):
        length = math.hypot(bx - ax, by - ay)
        n = max(2, int(length / rng.uniform(*step)))
        nx, ny = (by - ay) / length, -(bx - ax) / length
        for i in range(n):
            f = i / n
            j = rng.uniform(-amp, amp)
            pts.append((x0 + ax + (bx - ax) * f + nx * j, y0 + ay + (by - ay) * f + ny * j))
    return pts


def torn_paper(w, h, rng, color="#fbf5e6", shadow=True, texture=True):
    pad = 8

    def draw(d, k):
        pts = [(x * k, y * k) for x, y in jagged_poly(w, h, rng, x0=pad, y0=pad)]
        d.polygon(pts, fill=rgba(color))
    img = supersample(w + 2 * pad, h + 2 * pad, draw, k=2)
    if texture:
        noise = rng.normal(0, 6, (img.height, img.width)).astype(np.float32)
        arr = np.asarray(img).astype(np.float32)
        arr[..., :3] = np.clip(arr[..., :3] + noise[..., None], 0, 255)
        img = Image.fromarray(arr.astype(np.uint8), "RGBA")
    return drop_shadow(img, 0, 6, 8, (40, 25, 10, 90)) if shadow else img


def tape(w, h, rng, color=(242, 230, 176, 175)):
    pad = 4

    def draw(d, k):
        pts = []
        teeth = 5
        for i in range(teeth + 1):                                     # left zig-zag end
            pts.append(((pad + (3 if i % 2 else 0)) * k, (pad + h * i / teeth) * k))
        for i in range(teeth + 1):                                     # right zig-zag end
            pts.append(((pad + w - (3 if i % 2 else 0)) * k, (pad + h - h * i / teeth) * k))
        d.polygon(pts, fill=rgba(color))
    return supersample(w + 2 * pad, h + 2 * pad, draw, k=2)


def stroke_path(points, width, color, upto=1.0, pad=None):
    """Draw a polyline (as if by marker) up to a fraction of its length. Returns (img, (x0, y0))."""
    xs, ys = [p[0] for p in points], [p[1] for p in points]
    pad = pad or width + 4
    x0, y0 = min(xs) - pad, min(ys) - pad
    w, h = max(xs) - x0 + pad, max(ys) - y0 + pad
    lens = [0.0]
    for a, b in zip(points, points[1:]):
        lens.append(lens[-1] + math.hypot(b[0] - a[0], b[1] - a[1]))
    total = lens[-1] * clamp01(upto)
    part = [points[0]]
    for i in range(1, len(points)):
        if lens[i] <= total:
            part.append(points[i])
        else:
            a, b = points[i - 1], points[i]
            f = (total - lens[i - 1]) / max(lens[i] - lens[i - 1], 1e-6)
            part.append((a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f))
            break

    def draw(d, k):
        q = [((x - x0) * k, (y - y0) * k) for x, y in part]
        if len(q) > 1:
            d.line(q, fill=rgba(color), width=int(width * k), joint="curve")
        for x, y in (q[0], q[-1]):
            r = width * k / 2
            d.ellipse((x - r, y - r, x + r, y + r), fill=rgba(color))
    return supersample(w, h, draw, k=2), (x0, y0)


def wobble_line(x0, y0, x1, y1, rng, n=14, amp=3.0):
    return [(lerp(x0, x1, i / n) + rng.uniform(-amp, amp) * 0.3, lerp(y0, y1, i / n) + rng.uniform(-amp, amp))
            for i in range(n + 1)]


def squiggle(x0, x1, y, waves=4, amp=8, n=60):
    return [(lerp(x0, x1, i / n), y + amp * math.sin(i / n * waves * 2 * math.pi)) for i in range(n + 1)]


def scribble_circle(cx, cy, rx, ry, rng, turns=1.15, n=70):
    a0 = rng.uniform(0, 2 * math.pi)
    pts = []
    for i in range(n + 1):
        a = a0 + 2 * math.pi * turns * i / n
        k = 1 + 0.06 * math.sin(i / n * 7) + rng.uniform(-0.01, 0.01)
        pts.append((cx + rx * k * math.cos(a), cy + ry * k * math.sin(a)))
    return pts


def arrow_path(x0, y0, x1, y1, bend=0.25):
    mx, my = (x0 + x1) / 2, (y0 + y1) / 2
    nx, ny = -(y1 - y0) * bend, (x1 - x0) * bend
    pts = []
    for i in range(31):
        t = i / 30
        cx, cy = mx + nx, my + ny
        pts.append(((1 - t) ** 2 * x0 + 2 * (1 - t) * t * cx + t * t * x1,
                    (1 - t) ** 2 * y0 + 2 * (1 - t) * t * cy + t * t * y1))
    ang = math.atan2(y1 - pts[-3][1], x1 - pts[-3][0])
    head = 26
    left = (x1 - head * math.cos(ang - 0.5), y1 - head * math.sin(ang - 0.5))
    right = (x1 - head * math.cos(ang + 0.5), y1 - head * math.sin(ang + 0.5))
    return pts + [left, (x1, y1), right]


def radial(w, h, color, inner=0.0, outer=1.0, alpha=255, invert=False):
    """Elliptical radial gradient: opaque at the centre fading out (or the reverse with invert)."""
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    d = np.sqrt(((x - w / 2) / (w / 2)) ** 2 + ((y - h / 2) / (h / 2)) ** 2)
    a = np.clip((d - inner) / max(outer - inner, 1e-6), 0, 1)
    a = a if invert else 1 - a
    a = (a ** 1.6 * alpha).astype(np.uint8)
    c = rgba(color)
    arr = np.zeros((h, w, 4), np.uint8)
    arr[..., 0], arr[..., 1], arr[..., 2], arr[..., 3] = c[0], c[1], c[2], a
    return Image.fromarray(arr, "RGBA")


def asterisk(size, color="#FFFFFF", arms=6, width=0.2, glow_blur=None):
    """Hand-made looking asterisk with rounded arms (the whimsical sparkle)."""
    pad = size // 3

    def draw(d, k):
        c = (size / 2 + pad) * k
        r = size / 2 * k
        w = max(2, int(size * width * k))
        for i in range(arms):
            a = math.pi * i / arms + 0.2
            x0, y0 = c - r * math.cos(a), c - r * math.sin(a)
            x1, y1 = c + r * math.cos(a), c + r * math.sin(a)
            d.line((x0, y0, x1, y1), fill=rgba(color), width=w)
            for x, y in ((x0, y0), (x1, y1)):
                d.ellipse((x - w / 2, y - w / 2, x + w / 2, y + w / 2), fill=rgba(color))
    img = supersample(size + 2 * pad, size + 2 * pad, draw)
    return glow(img, glow_blur or max(2, size // 8), 1)


def pill(text, value=None, fill="#FFFFFF", ink="#1E1E1E", size=40, font_name="Figtree-Medium.ttf",
         value_font="Figtree-ExtraBold.ttf", min_w=0):
    """Rounded label chip, optionally 'label ........ value' like a stat card."""
    t = trim(text_img(text, font_name, size, ink, pad=2))
    v = trim(text_img(value, value_font, size, ink, pad=2)) if value else None
    h = int(size * 1.9)
    gap = int(size * 2.2) if v else 0
    w = max(min_w, t.width + (v.width + gap if v else 0) + int(size * 1.3))
    card = Image.new("RGBA", (w, h), (0, 0, 0, 0))

    def draw(d, k):
        d.rounded_rectangle((0, 0, (w - 1) * k, (h - 1) * k), radius=h * k / 2, fill=rgba(fill))
    card = supersample(w, h, draw)
    card.alpha_composite(t, (int(size * 0.65), (h - t.height) // 2))
    if v:
        card.alpha_composite(v, (w - v.width - int(size * 0.65), (h - v.height) // 2))
    return drop_shadow(card, 0, 4, 8, (40, 25, 15, 70))


def deco_star(kind, size, color="#FBD3E0", width=None):
    """Minimal decorative stars, drawn with thin lines:
    burst   8 thin rays, long and short alternating (a twinkle of light)
    outline a small five-point star drawn as an outline
    spark   a slim four-point star with two tiny dots beside it
    cross   a thin plus-shaped glint with a soft dot in the middle
    asterisk six thin rays of equal length
    heart   a tiny outline heart"""
    wdt = width or max(2, size // 16)
    pad = wdt * 3

    def draw(d, k):
        c = (size / 2 + pad) * k
        r = size / 2 * k
        col = rgba(color)
        lw = max(1, int(wdt * k))

        def ray(a, length):
            x, y = c + math.cos(a) * length, c + math.sin(a) * length
            d.line((c, c, x, y), fill=col, width=lw)
            d.ellipse((x - lw / 2, y - lw / 2, x + lw / 2, y + lw / 2), fill=col)
        if kind == "burst":
            for i in range(8):
                ray(-math.pi / 2 + i * math.pi / 4, r * (1.0 if i % 2 == 0 else 0.55))
        elif kind == "asterisk":
            for i in range(6):
                ray(-math.pi / 2 + i * math.pi / 3, r * 0.9)
        elif kind == "cross":
            for i in range(4):
                ray(i * math.pi / 2, r)
            d.ellipse((c - lw * 1.4, c - lw * 1.4, c + lw * 1.4, c + lw * 1.4), fill=col)
        elif kind == "outline":
            pts = []
            for i in range(11):
                a = -math.pi / 2 + i * math.pi / 5
                rr = r * (0.95 if i % 2 == 0 else 0.42)
                pts.append((c + rr * math.cos(a), c + rr * math.sin(a)))
            d.line(pts, fill=col, width=lw, joint="curve")
        elif kind == "spark":
            pts = []
            for i in range(120):
                a = 2 * math.pi * i / 120
                ca, sa = math.cos(a), math.sin(a)
                pts.append((c + r * 0.7 * math.copysign(abs(ca) ** 4, ca), c + r * math.copysign(abs(sa) ** 4, sa)))
            d.polygon(pts, fill=col)
            for dx, dy, rr in ((0.75, -0.55, 0.09), (0.95, -0.2, 0.06)):
                d.ellipse((c + dx * r - rr * r, c + dy * r - rr * r, c + dx * r + rr * r, c + dy * r + rr * r), fill=col)
        elif kind == "heart":
            pts = []
            for i in range(90):
                t = 2 * math.pi * i / 89
                x = 16 * math.sin(t) ** 3
                y = -(13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t))
                pts.append((c + x * r / 17, c + y * r / 17))
            d.line(pts, fill=col, width=lw, joint="curve")
    img = supersample(size + 2 * pad, size + 2 * pad, draw, k=3)
    return glow(img, max(2, size // 14), 1.2)
