"""Overlay effects: checklist, floating phone, note wall, headline wall, chart grow, orbit.
Wall, chart and the back half of the orbit sit BEHIND the speaker when a cutout exists."""
import math

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from common import H, SAFE, W
from effects.base import Effect, clips_thumbs, cover, rounded, user_image
from gfx import (drop_shadow, font, lerp, out_back, out_cubic, prog, rgba, stroke_path, supersample, text_img, trim,
                 xform)

BUTTER = "#FFE45C"
SANS = "Figtree-Medium.ttf"
BOLD = "Figtree-ExtraBold.ttf"
SERIF = "PlayfairDisplay-SemiBold.ttf"


def put(frame, img, cx, cy):
    if img is not None:
        frame.paste(img, (int(cx - img.width / 2), int(cy - img.height / 2)), img)


def wrap(text, fnt, size, width):
    f = font(fnt, size)
    lines, cur = [], ""
    for w in text.split():
        trial = f"{cur} {w}".strip()
        if cur and f.getlength(trial) > width:
            lines.append(cur)
            cur = w
        else:
            cur = trial
    return lines + ([cur] if cur else [])


# ---------------------------------------------------------------- 7. checklist
class Checklist(Effect):
    """Frosted dark card with a to-do list; each item ticks off on its time. Options: title, items[],
    at[] (tick times, default evenly spread)."""
    name = "checklist"
    reserves = "top"

    def __init__(self, spec, ctx):
        super().__init__(spec, ctx)
        self.items = spec.get("items", ["step one", "step two", "step three"])
        n = len(self.items)
        span = self.end - self.start
        self.at = spec.get("at") or [self.start + span * (i + 0.8) / (n + 0.6) for i in range(n)]
        self.title = spec.get("title", "all you need to do").upper()
        self.w, self.row = 860, 92
        self.h = 120 + self.row * n

    def front(self, frame, t):
        e = self.env(t)
        if e <= 0.01:
            return
        y = self.ctx.block_y(self.start, self.h + 20, prefer="top")
        x0, y0 = int((W - self.w) / 2), int(y - self.h / 2 + (1 - e) * -40)
        region = frame.crop((x0, y0, x0 + self.w, y0 + self.h)).filter(ImageFilter.GaussianBlur(18))
        card = Image.blend(region, Image.new("RGB", region.size, (22, 22, 24)), 0.62).convert("RGBA")
        d = ImageDraw.Draw(card)
        d.ellipse((40, 46, 52, 58), fill=rgba(BUTTER))
        d.text((64, 36), self.title, fill=(200, 200, 200), font=font(BOLD, 26))
        done = sum(t >= a for a in self.at)
        d.text((self.w - 120, 36), f"{done} of {len(self.items)}", fill=(170, 170, 170), font=font(SANS, 26))
        for i, item in enumerate(self.items):
            yy = 100 + i * self.row
            k = out_back(prog(t, self.at[i], 0.3), 2.2)
            cx, cy = 66, yy + 30
            if k > 0:
                r = 22 * k
                d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=rgba(BUTTER))
                if k > 0.6:
                    d.line((cx - 10, cy + 1, cx - 3, cy + 9, cx + 11, cy - 8), fill=(30, 30, 30), width=5)
            else:
                d.ellipse((cx - 22, cy - 22, cx + 22, cy + 22), outline=(140, 140, 140), width=3)
            col = (255, 255, 255) if t >= self.at[i] else (150, 150, 150)
            d.text((110, yy + 10), item, fill=col, font=font(BOLD if t >= self.at[i] else SANS, 40))
        card = rounded(card, 36)
        card.putalpha(card.getchannel("A").point(lambda v: int(v * e)))
        frame.paste(card, (x0, y0), card)


# ---------------------------------------------------------------- 8. floating phone (phone mockup)
class PhoneFloat(Effect):
    """A phone floats in beside you showing a screenshot (image) or a chat that writes itself (messages[])."""
    name = "phone-float"
    reserves = "bottom"

    def __init__(self, spec, ctx):
        super().__init__(spec, ctx)
        self.pw, self.ph = 330, 680
        self.screen = None
        if spec.get("image"):
            self.screen = rounded(cover(user_image(ctx, spec["image"]), self.pw - 24, self.ph - 24), 38)
        self.messages = spec.get("messages", ["can you edit my reel?", "on it ✨ picking your best takes"])
        self.title = spec.get("title", "assistant")

    def _phone(self, t):
        img = Image.new("RGBA", (self.pw, self.ph), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        d.rounded_rectangle((0, 0, self.pw - 1, self.ph - 1), radius=50, fill=(18, 18, 20))
        if self.screen is not None:
            img.paste(self.screen, (12, 12), self.screen)
        else:
            d.rounded_rectangle((12, 12, self.pw - 13, self.ph - 13), radius=38, fill=(250, 249, 246))
            d.text((40, 70), self.title, fill=(40, 40, 40), font=font(BOLD, 24))
            y = 130
            local = t - self.start - 0.4
            for i, m in enumerate(self.messages):
                if local < i * 1.1:
                    break
                mine = i % 2 == 0
                lines = wrap(m, SANS, 22, 200)
                bh = 22 + 28 * len(lines)
                x0 = self.pw - 260 if mine else 30
                d.rounded_rectangle((x0, y, x0 + 230, y + bh), radius=18,
                                    fill=(40, 120, 255) if mine else (232, 230, 226))
                for j, ln in enumerate(lines):
                    d.text((x0 + 16, y + 10 + 28 * j), ln, fill="white" if mine else (30, 30, 30), font=font(SANS, 22))
                y += bh + 16
        d.rounded_rectangle((self.pw / 2 - 50, 24, self.pw / 2 + 50, 50), radius=13, fill=(18, 18, 20))
        return drop_shadow(img, 0, 16, 24, (0, 0, 0, 120))

    def front(self, frame, t):
        e = self.env(t)
        if e <= 0.01:
            return
        cx, cy, top, chin = self.face(t)
        right = cx < W / 2 + 40
        s = 0.85
        hw, hh = self.pw * s / 2, self.ph * s / 2
        y = min(max(chin - hh * 0.2, SAFE["top"] + hh), SAFE["bottom"] - hh * 0.6)
        x = W - hw - 40 if right else hw + 40
        box = self.ctx.face_core(self.ctx.seg_at(t))
        if box is not None:                       # slide toward the edge until the phone clears the face
            if right and x - hw < box[2] + 20:
                x = min(box[2] + 20 + hw, W + hw * 0.3)
            if not right and x + hw > box[0] - 20:
                x = max(box[0] - 20 - hw, -hw * 0.3)
        img = xform(self._phone(t), scale=s * lerp(0.7, 1, out_back(e, 1.4)), rot=-6 if right else 6, alpha=e)
        put(frame, img, x + (1 - e) * (300 if right else -300), y + 8 * math.sin(t * 1.6))


# ---------------------------------------------------------------- 9. note wall / headline wall
class NoteWall(Effect):
    """Notes pop up on the wall behind you, one after another. Options: notes[] (text) or images[]; every."""
    name = "note-wall"
    needs_matte = True
    reserves = "top"
    headline = False

    def __init__(self, spec, ctx):
        super().__init__(spec, ctx)
        r = np.random.default_rng(int(spec.get("seed", 4)))
        texts = spec.get("notes") or spec.get("headlines") or ["note one", "note two", "note three"]
        imgs = [user_image(ctx, p) for p in spec.get("images", [])]
        self.cards = [self._card(x, i, r) for i, x in enumerate(texts)] + [self._img_card(im, r) for im in imgs]
        cols = 3
        self.spots = []
        for i, card in enumerate(self.cards):
            col, row = i % cols, i // cols
            hw = card.width / 2
            x = W / 2 + (col - 1) * 330 + r.uniform(-30, 30)
            x = min(max(x, SAFE["left"] + hw), SAFE["right"] - hw)
            y = SAFE["top"] + 110 + row * 210 + r.uniform(-30, 30)
            self.spots.append((x, min(y, 1250), r.uniform(-7, 7)))
        self.every = float(spec.get("every", 0.22 if self.headline else 0.35))

    def _card(self, text, i, r):
        if self.headline:
            style = i % 3
            bg, fg, fnt = [((255, 255, 255), (20, 20, 20), SERIF), ((18, 18, 18), (255, 255, 255), BOLD),
                           ((246, 240, 225), (30, 30, 30), SERIF)][style]
            size, width = 38, 300
        else:
            bg, fg, fnt, size, width = (255, 255, 255), (35, 35, 35), SANS, 30, 260
        lines = wrap(text, fnt, size, width)
        h = 40 + int(size * 1.25) * len(lines)
        card = Image.new("RGBA", (width + 40, h), bg + (255,))
        d = ImageDraw.Draw(card)
        for j, ln in enumerate(lines):
            d.text((20, 20 + int(size * 1.25) * j), ln, fill=fg, font=font(fnt, size))
        return drop_shadow(rounded(card, 8 if self.headline else 16), 0, 8, 12, (0, 0, 0, 110))

    def _img_card(self, im, r):
        im = im.copy()
        im.thumbnail((300, 300))
        return drop_shadow(rounded(im, 14), 0, 8, 12, (0, 0, 0, 110))

    def behind(self, bg, t):
        out = 1 - out_cubic(prog(t, self.end - 0.25, 0.25))
        for i, (card, (x, y, rot)) in enumerate(zip(self.cards, self.spots)):
            k = out_back(prog(t, self.start + i * self.every, 0.3), 2.0)
            if k > 0:
                put(bg, xform(card, scale=k, rot=rot, alpha=min(1, k) * out), x, y)

    def front(self, frame, t):
        if self.ctx_matte is None:              # no cutout: show the notes in front, but off the face
            for i, (card, (x, y, rot)) in enumerate(zip(self.cards, self.spots)):
                if not self.ctx.hits_face(t, x, y, card.width / 2):
                    k = out_back(prog(t, self.start + i * self.every, 0.3), 2.0)
                    if k > 0:
                        put(frame, xform(card, scale=k, rot=rot, alpha=min(1, k) * self.env(t)), x, y)


class HeadlineWall(NoteWall):
    """Like the note wall, but rapid-fire newspaper headlines (headlines[])."""
    name = "headline-wall"
    headline = True


# ---------------------------------------------------------------- 10. chart grow
class ChartGrow(Effect):
    """A glowing line chart draws itself behind you and lands on a label. Options: label, labels[] (x axis),
    points[] (0..1 heights)."""
    name = "chart-grow"
    needs_matte = True
    reserves = "top"

    def __init__(self, spec, ctx):
        super().__init__(spec, ctx)
        self.labels = spec.get("labels", ["M", "T", "W", "T", "F", "S", "S"])
        self.points = spec.get("points", [0.05, 0.12, 0.1, 0.25, 0.38, 0.62, 0.95])
        self.label = spec.get("label", "growth ↗")
        self.x0, self.x1 = 100, W - 100
        _, _, top, _ = self.face(self.start)
        self.y0 = SAFE["top"] + 90
        self.y1 = min(1150, max(self.y0 + 330, top + 160))   # keep most of the chart above the head
        self.grid = self._grid()
        self.tag = self._tag()
        self.cache = {}

    def _grid(self):
        img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        n = len(self.labels)
        for i, lab in enumerate(self.labels):
            x = self.x0 + (self.x1 - self.x0) * i / (n - 1)
            for y in range(self.y0 + 40, self.y1, 22):
                d.line((x, y, x, y + 10), fill=(255, 255, 255, 70), width=2)
            d.text((x - 10, self.y0 - 6), lab, fill=(255, 255, 255, 200), font=font(BOLD, 30))
        return img

    def _tag(self):
        txt = text_img(self.label.upper(), BOLD, 34, "#1E1E1E", pad=2)
        txt = trim(txt)
        w, h = txt.width + 44, txt.height + 26

        def pill(d, k):
            d.rounded_rectangle((0, 0, w * k - 1, h * k - 1), radius=h * k / 2, fill=rgba(BUTTER))
        card = supersample(w, h, pill)
        card.alpha_composite(txt, (22, 13))
        return drop_shadow(card, 0, 6, 10, (0, 0, 0, 110))

    def _pts(self):
        n = len(self.points)
        return [(self.x0 + (self.x1 - self.x0) * i / (n - 1), self.y1 - (self.y1 - self.y0 - 60) * p)
                for i, p in enumerate(self.points)]

    def behind(self, bg, t):
        e = self.env(t)
        if e <= 0.01:
            return
        bg.paste(xform(self.grid, alpha=e), (0, 0), xform(self.grid, alpha=e))
        p = round(out_cubic(prog(t, self.start + 0.3, max(0.6, (self.end - self.start) * 0.55))) * 24) / 24
        if p > 0:
            if p not in self.cache:
                line, (ox, oy) = stroke_path(_smooth(self._pts()), 9, BUTTER, upto=p)
                glow = line.filter(ImageFilter.GaussianBlur(12))
                g = Image.new("RGBA", line.size, (0, 0, 0, 0))
                g.alpha_composite(glow)
                g.alpha_composite(glow)
                g.alpha_composite(line)
                self.cache[p] = (g, ox, oy)
            g, ox, oy = self.cache[p]
            g = xform(g, alpha=e)
            bg.paste(g, (int(ox), int(oy)), g)
        k = out_back(prog(t, self.start + 0.3 + (self.end - self.start) * 0.55, 0.35), 2)
        if k > 0:
            x, y = self._pts()[-1]
            put(bg, xform(self.tag, scale=k, alpha=e), min(x - 40, W - 160), y - 70)

    def front(self, frame, t):
        if self.ctx_matte is None:
            self.behind(frame, t)


def _smooth(pts, n=12):
    out = []
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        for i in range(n):
            f = i / n
            s = f * f * (3 - 2 * f)
            out.append((x0 + (x1 - x0) * f, y0 + (y1 - y0) * s))
    out.append(pts[-1])
    return out


# ---------------------------------------------------------------- 11. orbit
class Orbit(Effect):
    """Your photos or clips circle around you, passing behind and in front. Options: images[] (else stills from
    the reel), count, speed."""
    name = "orbit"
    needs_matte = True

    def __init__(self, spec, ctx):
        super().__init__(spec, ctx)
        n = int(spec.get("count", 6))
        imgs = [cover(user_image(ctx, p), 170, 300) for p in spec.get("images", [])][:n] or clips_thumbs(ctx, n)
        self.tiles = []
        for im in imgs:
            card = Image.new("RGB", (im.width + 12, im.height + 12), (255, 255, 255))
            card.paste(im, (6, 6))
            self.tiles.append(drop_shadow(rounded(card, 18), 0, 8, 12, (0, 0, 0, 120)))
        self.speed = float(spec.get("speed", 0.35))

    def _positions(self, t):
        cx, cy, top, chin = self.face(t)
        oy = min(chin + 80, SAFE["bottom"] - 200)
        out = []
        for i, tile in enumerate(self.tiles):
            a = 2 * math.pi * (i / len(self.tiles) + (t - self.start) * self.speed * 0.25)
            depth = math.sin(a)
            out.append((tile, cx + 400 * math.cos(a), oy + 150 * depth - 120, depth))
        return out

    def _draw(self, frame, t, front):
        e = self.env(t)
        for tile, x, y, depth in sorted(self._positions(t), key=lambda p: p[3]):
            if (depth > 0) != front:
                continue
            s = (0.75 + 0.25 * (depth + 1) / 2) * lerp(0.4, 1, e)
            put(frame, xform(tile, scale=s, alpha=e * (0.75 + 0.25 * (depth + 1) / 2), rot=-depth * 4), x, y)

    def behind(self, bg, t):
        self._draw(bg, t, front=False)

    def front(self, frame, t):
        if self.ctx_matte is None:
            self._draw(frame, t, front=False)
        self._draw(frame, t, front=True)
