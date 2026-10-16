"""Shiny 3D "dazzle" stickers rendered from scratch: chrome and gold stars, jelly flowers, faceted rhinestone
hearts and flowers, iridescent sequins, a holographic glass heart, a disco ball and chrome sparkles.

Each gem is a 2D shape turned into a height field (blurred mask), lit with diffuse + specular light and a
material (chrome reflection bands, jelly translucency, flat facets, rainbow film). Pure numpy + OpenCV.
"""
import math

import cv2
import numpy as np
from PIL import Image, ImageDraw

from gfx import drop_shadow, rgba

K = 3                                   # supersampling factor
LIGHT = np.array([-0.45, -0.65, 0.9])
LIGHT = LIGHT / np.linalg.norm(LIGHT)
HALF = LIGHT + np.array([0, 0, 1.0])
HALF = HALF / np.linalg.norm(HALF)


# ---------------------------------------------------------------- shapes (polygons in a size x size box)
def _star(size, points=5, inner=0.48):
    c = size / 2
    pts = []
    for i in range(points * 2):
        a = -math.pi / 2 + i * math.pi / points
        r = c * 0.92 * (1 if i % 2 == 0 else inner)
        pts.append((c + r * math.cos(a), c + r * math.sin(a)))
    return pts


def _flower(size, petals=5, depth=0.32):
    c = size / 2
    return [(c + c * 0.92 * (1 - depth + depth * abs(math.cos(petals * a / 2))) * math.cos(a),
             c + c * 0.92 * (1 - depth + depth * abs(math.cos(petals * a / 2))) * math.sin(a))
            for a in np.linspace(0, 2 * math.pi, 240, endpoint=False)]


def _heart(size):
    out = []
    for t in np.linspace(0, 2 * math.pi, 240, endpoint=False):
        x = 16 * math.sin(t) ** 3
        y = -(13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t))
        out.append((size / 2 + x * size / 36, size / 2 + y * size / 36 + size * 0.04))
    return out


def _sparkle4(size):
    c = size / 2
    out = []
    for a in np.linspace(0, 2 * math.pi, 240, endpoint=False):
        ca, sa = math.cos(a), math.sin(a)
        out.append((c + c * 0.95 * math.copysign(abs(ca) ** 3.4, ca), c + c * 0.95 * math.copysign(abs(sa) ** 3.4, sa)))
    return out


def _circle(size):
    c = size / 2
    return [(c + c * 0.92 * math.cos(a), c + c * 0.92 * math.sin(a)) for a in np.linspace(0, 2 * math.pi, 200, endpoint=False)]


def _mask(pts, size, hole=0.0):
    img = Image.new("L", (size * K, size * K), 0)
    d = ImageDraw.Draw(img)
    d.polygon([(x * K, y * K) for x, y in pts], fill=255)
    if hole:
        c, r = size * K / 2, size * K * hole / 2
        d.ellipse((c - r, c - r, c + r, c + r), fill=0)
    return np.asarray(img, np.float32) / 255


# ---------------------------------------------------------------- lighting
def _normals(mask, puff=0.5, strength=1.0):
    """Height from the distance to the edge: a rounded bevel `puff` of the way in (1.0 = full dome)."""
    m8 = (mask > 0.5).astype(np.uint8)
    dist = cv2.distanceTransform(m8, cv2.DIST_L2, 5).astype(np.float32)
    r = max(dist.max() * puff, 1.0)
    x = np.clip(dist / r, 0, 1)
    h = np.sqrt(1 - (1 - x) ** 2) * r * strength
    h = cv2.GaussianBlur(h, (0, 0), 1.2)
    gy, gx = np.gradient(h)
    n = np.dstack([-gx, -gy, np.ones_like(h)])
    return n / np.linalg.norm(n, axis=2, keepdims=True), x


def _shade(n):
    diffuse = np.clip(n @ LIGHT, 0, 1)
    spec = np.clip(n @ HALF, 0, 1)
    return diffuse, spec


def _hsv_to_rgb(h, s, v):
    h = (h % 1.0) * 6
    i = np.floor(h).astype(int) % 6
    f = h - np.floor(h)
    p, q, t = v * (1 - s), v * (1 - s * f), v * (1 - s * (1 - f))
    r = np.choose(i, [v, q, p, p, t, v])
    g = np.choose(i, [t, v, v, q, p, p])
    b = np.choose(i, [p, p, t, v, v, q])
    return np.dstack([r, g, b])


def _finish(rgb, mask, size, shadow=True):
    rgb = np.clip(rgb, 0, 1)
    arr = np.dstack([rgb * 255, mask * 255]).astype(np.uint8)
    img = Image.fromarray(arr, "RGBA").resize((size, size), Image.LANCZOS)
    return drop_shadow(img, 0, max(3, size // 22), max(3, size // 18), (40, 25, 30, 95)) if shadow else img


# ---------------------------------------------------------------- materials
def chrome(pts, size, tint=(1, 1, 1), puff=1.0):
    m = _mask(pts, size)
    n, _ = _normals(m, puff, 0.9)
    diffuse, spec = _shade(n)
    # reflection of a bright sky above a dark horizon: banded by the normal's vertical component
    ny = n[..., 1]
    env = 0.62 + 0.38 * np.tanh(-ny * 5) - 0.42 * np.exp(-((ny - 0.12) * 9) ** 2) + 0.18 * n[..., 0]
    v = np.clip(env * 0.75 + diffuse * 0.35, 0, 1)[..., None] * np.array(tint)
    v = v + (spec ** 60)[..., None] * 1.2
    return _finish(v, m, size)


def jelly(pts, size, color, puff=0.35, center=None):
    m = _mask(pts, size)
    n, h = _normals(m, puff, 0.6)
    diffuse, spec = _shade(n)
    base = np.array(rgba(color)[:3]) / 255
    glow = (0.55 + 0.25 * h)[..., None]                      # thicker middle looks lighter (light passes through)
    glow = 0.78 + 0.1 * glow
    v = base * (glow + 0.22 * diffuse[..., None]) + (spec ** 60)[..., None] * 0.9
    v += (np.clip(1 - n[..., 2], 0, 1) ** 1.5)[..., None] * 0.15   # bright rim
    if center:
        s = m.shape[0]
        yy, xx = np.mgrid[0:s, 0:s]
        d = np.hypot(xx - s / 2, yy - s / 2) / (s / 2)
        c = np.array(rgba(center)[:3]) / 255
        dot = np.clip((0.2 - d) / 0.05, 0, 1)[..., None]
        v = v * (1 - dot) + (c * (0.8 + 0.4 * (spec ** 8)[..., None])) * dot
    return _finish(v, m * 0.97, size)


def faceted(pts, size, color, facets=10):
    m = _mask(pts, size)
    n, h = _normals(m, 1.0, 1.0)
    ang = np.arctan2(n[..., 1], n[..., 0])
    tilt = np.hypot(n[..., 0], n[..., 1])
    qa = (np.round(ang / (2 * np.pi / facets)) * (2 * np.pi / facets))
    qt = np.where(tilt < 0.25, 0.0, np.where(tilt < 0.6, 0.45, 0.8))      # table, crown and pavilion rings
    fn = np.dstack([np.cos(qa) * qt, np.sin(qa) * qt, np.sqrt(np.clip(1 - qt ** 2, 0, 1))])
    diffuse, spec = _shade(fn)
    base = np.array(rgba(color)[:3]) / 255
    v = base * (0.25 + 1.0 * diffuse[..., None] ** 1.5) + (spec ** 30)[..., None] * 1.0
    edges = (np.abs(np.gradient(qa)[0]) + np.abs(np.gradient(qa)[1]) + np.abs(np.gradient(qt)[0]) + np.abs(np.gradient(qt)[1])) > 0.01
    v = v * (1 - 0.25 * cv2.GaussianBlur(edges.astype(np.float32), (0, 0), 1.0))[..., None]
    v += ((qa * 7.3) % 1 > 0.85)[..., None] * 0.18 * (qt > 0)[..., None]   # scattered bright facets
    return _finish(v, m, size)


def iridescent(pts, size, hole=0.0, puff=0.6, film=1.0):
    m = _mask(pts, size, hole)
    n, h = _normals(m, puff, 0.5)
    diffuse, spec = _shade(n)
    s = m.shape[0]
    yy, xx = np.mgrid[0:s, 0:s]
    sweep = (xx + yy * 0.6) / s                                  # thin-film colour shifts across the disc
    hue = (0.9 + sweep * 0.45 * film + h * 0.12) % 1.0
    rainbow = _hsv_to_rgb(hue, np.full_like(hue, 0.6), np.full_like(hue, 1.0))
    v = rainbow * (0.55 + 0.5 * diffuse[..., None]) + (spec ** 25)[..., None] * 0.9
    return _finish(v, m, size)


def holo_glass(pts, size, seed=3):
    m = _mask(pts, size)
    n, h = _normals(m, 0.5, 0.9)
    diffuse, spec = _shade(n)
    s = m.shape[0]
    r = np.random.default_rng(seed)
    noise = cv2.resize(r.random((5, 5)).astype(np.float32), (s, s), interpolation=cv2.INTER_CUBIC)
    flakes = cv2.resize(r.random((70, 70)).astype(np.float32), (s, s), interpolation=cv2.INTER_NEAREST)
    hue = (noise * 0.9 + flakes * 0.12 + 0.45) % 1
    holo = _hsv_to_rgb(hue, np.full_like(hue, 0.55), 0.6 + 0.4 * flakes ** 2)
    rim = np.clip(1 - n[..., 2], 0, 1) ** 0.8
    inner = cv2.erode(m, np.ones((int(s * 0.07),) * 2, np.uint8))
    v = holo * inner[..., None] * 0.85 + (1 - inner)[..., None] * (0.85 + 0.15 * diffuse[..., None])
    v = v * (0.75 + 0.3 * diffuse[..., None]) + (spec ** 50)[..., None] * 1.2 + rim[..., None] * 0.25
    return _finish(v, m, size)


def disco(size, seed=5):
    pts = _circle(size)
    m = _mask(pts, size)
    s = m.shape[0]
    yy, xx = np.mgrid[0:s, 0:s].astype(np.float32)
    x, y = (xx - s / 2) / (s / 2 * 0.92), (yy - s / 2) / (s / 2 * 0.92)
    z = np.sqrt(np.clip(1 - x ** 2 - y ** 2, 0, 1))
    lat, lon = np.arcsin(np.clip(y, -1, 1)), np.arctan2(x, z)
    rows, cols = 12, 16
    ti, tj = np.floor((lat / np.pi + 0.5) * rows), np.floor((lon / np.pi + 0.5) * cols)
    r = np.random.default_rng(seed)
    tile_val = r.uniform(0.35, 1.0, (rows + 1, cols + 1))
    tv = tile_val[ti.astype(int).clip(0, rows), tj.astype(int).clip(0, cols)]
    gap = (((lat / np.pi + 0.5) * rows) % 1 < 0.1) | (((lon / np.pi + 0.5) * cols) % 1 < 0.1)
    n = np.dstack([x, y, z])
    diffuse, spec = _shade(n)
    v = (tv * (0.45 + 0.55 * diffuse)) * (~gap) + gap * 0.18
    v = np.dstack([v, v, v * 1.05]) + (spec ** 30)[..., None] * 0.6 * (tv > 0.85)[..., None]
    return _finish(v, m, size)


def acrylic(pts, size, color, center=None, height=0.38, table=0.0):
    """Cut acrylic craft gem: flat faces from the centre to each pair of outline points (a star becomes a pyramid,
    a heart or circle a faceted dome), optional flat table on top; saturated see-through colour, bright facet
    sparkles and a white glint."""
    m = _mask(pts, size)
    s = m.shape[0]
    cx, cy = [v * K for v in (center or (size / 2, size / 2))]
    vx = np.array([p[0] * K for p in pts])
    vy = np.array([p[1] * K for p in pts])
    va = np.arctan2(vy - cy, vx - cx)
    order = np.argsort(va)
    vx, vy, va = vx[order], vy[order], va[order]
    yy, xx = np.mgrid[0:s, 0:s].astype(np.float32)
    pa = np.arctan2(yy - cy, xx - cx)
    i = (np.searchsorted(va, pa) - 1) % len(va)
    j = (i + 1) % len(va)
    R = np.hypot(vx - cx, vy - cy).max()
    hz = R * height
    # face through the apex (cx, cy, hz) and the two outline points: normal = (A - P1) x (P2 - P1)
    ax_, ay_ = cx - vx[i], cy - vy[i]
    bx_, by_ = vx[j] - vx[i], vy[j] - vy[i]
    nx, ny, nz = ay_ * 0 - hz * by_, hz * bx_ - ax_ * 0, ax_ * by_ - ay_ * bx_
    n = np.dstack([nx, ny, nz])
    n = n * np.sign(n[..., 2:3] + 1e-9)
    n = n / (np.linalg.norm(n, axis=2, keepdims=True) + 1e-9)
    if table:
        r = np.hypot(xx - cx, yy - cy) / R
        flat = r < table
        n[flat] = (0, 0, 1)
    diffuse, spec = _shade(n)
    base = np.array(rgba(color)[:3]) / 255
    face_id = np.where(np.hypot(xx - cx, yy - cy) < table * R, -1, i) if table else i
    sparkle = ((face_id * 0.6180339) % 1.0)[..., None]
    v = base * (0.5 + 0.55 * diffuse[..., None] ** 1.3 + 0.25 * sparkle) + (1 - base) * 0.18 * sparkle
    v += (spec ** 24)[..., None] * 0.95
    edge = np.zeros(m.shape, np.float32)
    edge[:, 1:] += (face_id[:, 1:] != face_id[:, :-1])
    edge[1:, :] += (face_id[1:, :] != face_id[:-1, :])
    v += cv2.GaussianBlur(np.clip(edge, 0, 1), (0, 0), 0.8)[..., None] * 0.22
    rim = cv2.GaussianBlur(m, (0, 0), K * 2.0)
    v = v * (0.72 + 0.28 * np.clip(rim * 1.6 - 0.3, 0, 1))[..., None]          # deeper colour at the edges
    gx, gy = cx - R * 0.32, cy - R * 0.38                                        # one soft white glint
    glint = np.exp(-(((xx - gx) / (R * 0.16)) ** 2 + ((yy - gy) / (R * 0.1)) ** 2))
    v += glint[..., None] * 0.45
    return _finish(v, m, size)


ACRYLIC = {"pink": "#F2148C", "blue": "#2BB8E8", "lilac": "#A472E0", "yellow": "#F9C80E", "red": "#E8231F",
           "green": "#7ED321", "clear": "#D9E4EE", "rose": "#F7A1C4"}

# ---------------------------------------------------------------- catalogue
KINDS = ["chrome-star", "gold-star", "jelly-flower-pink", "jelly-flower-peach", "jelly-flower-lilac",
         "rhinestone-heart", "rhinestone-flower", "sequin", "holo-heart", "disco", "chrome-sparkle", "jelly-star"] + \
        [f"acrylic-{shape}-{c}" for shape in ("star", "heart", "round") for c in ACRYLIC]


def gem(kind, size=110, seed=1):
    size = int(size)
    if kind == "chrome-star":
        return chrome(_star(size, inner=0.5), size)
    if kind == "gold-star":
        return chrome(_star(size, inner=0.45), size, tint=(1.0, 0.82, 0.32))
    if kind == "jelly-star":
        return jelly(_star(size, inner=0.55), size, "#F7D23E")
    if kind.startswith("jelly-flower"):
        col = {"pink": "#F4A6D8", "peach": "#EFA27A", "lilac": "#C7B2F2"}[kind.rsplit("-", 1)[1]]
        return jelly(_flower(size), size, col, center="#FFFFFF" if kind.endswith("peach") else "#E2238A")
    if kind == "rhinestone-heart":
        return faceted(_heart(size), size, "#E8155B")
    if kind == "rhinestone-flower":
        return faceted(_flower(size, 6, 0.35), size, "#FF3D7F", facets=12)
    if kind == "sequin":
        return iridescent(_circle(size), size, hole=0.18)
    if kind == "holo-heart":
        return holo_glass(_heart(size), size, seed)
    if kind == "disco":
        return disco(size, seed)
    if kind == "chrome-sparkle":
        return chrome(_sparkle4(size), size, tint=(0.92, 0.86, 1.0))
    if kind.startswith("acrylic-"):
        _, shape, col = kind.split("-", 2)
        c = ACRYLIC.get(col, col)
        if shape == "star":
            return acrylic(_star(size, inner=0.46), size, c, height=0.3)
        if shape == "heart":
            pts = _heart(size)
            return acrylic(pts[::12], size, c, center=(size / 2, size * 0.52), height=0.42, table=0.32)
        if shape == "round":
            return acrylic(_circle(size)[::12], size, c, height=0.45, table=0.42)
    raise ValueError(f"unknown gem {kind}")


if __name__ == "__main__":
    import sys
    out = Image.new("RGBA", (8 * 180, ((len(KINDS) + 7) // 8) * 180), (240, 236, 228, 255))
    for i, k in enumerate(KINDS):
        g = gem(k, 140)
        out.alpha_composite(g, (i % 8 * 180 + (180 - g.width) // 2, i // 8 * 180 + (180 - g.height) // 2))
    out.convert("RGB").save(sys.argv[1] if len(sys.argv) > 1 else "gems.jpg", quality=92)
