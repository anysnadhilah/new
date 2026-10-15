"""SCRAPBOOK: a collage journal page come to life. Headline-style captions that mix three type treatments
(chunky rounded white with a pink glow, pink serif, yellow italic serif), shiny 3D gem stickers that pop in and
glint around the words (chrome stars, jelly flowers, rhinestones, sequins, a disco ball), taped photo and note
cut-outs, camera-shutter flashes on cuts."""
import math
from pathlib import Path

import numpy as np
from PIL import Image

from common import H, SAFE, W
from gems import KINDS, gem
from gfx import (drop_shadow, lerp, out_back, out_cubic, place, prog, sparkle, tape, text_img, torn_paper,
                 xform)
from styles.base import Style, ease_sin

PINK = "#F79ACB"
HOT_PINK = "#EE5FA7"
YELLOW = "#F6E27A"
BROWN = "#3A2618"
WHITE = "#FFFFFF"
INK = "#2A2420"
ROUND = "Nunito-Black.ttf"
PINK_SERIF = "PlayfairDisplay-SemiBold.ttf"
ITALIC = "Fraunces-SemiBoldItalic.ttf"
HAND = "ShadowsIntoLight-Regular.ttf"
SMALL_SHADOW = (0, 3, 8, (40, 10, 30, 140))


def headline(text, size):
    """Chunky rounded white with a pink outline and pink glow ("bookish trip")."""
    return text_img(text.lower(), ROUND, size, WHITE, stroke=max(4, size // 18), stroke_fill=HOT_PINK,
                    tracking=-0.02, shadow=(0, 0, size // 7, (238, 95, 167, 210)))


def pink_serif(text, size):
    return text_img(text, PINK_SERIF, size, PINK, stroke=2, stroke_fill="#B23A78", tracking=-0.03,
                    shadow=(0, 3, 7, (60, 10, 40, 190)))


def yellow_italic(text, size):
    return text_img(text.lower(), ITALIC, size, YELLOW, stroke=max(3, size // 22), stroke_fill=BROWN,
                    tracking=-0.01, shadow=(0, 3, 6, (40, 20, 10, 120)))


RECIPES = [pink_serif, yellow_italic]
GEM_ROTATION = ["chrome-star", "jelly-flower-pink", "rhinestone-heart", "sequin", "gold-star", "chrome-sparkle",
                "jelly-flower-peach", "holo-heart", "disco", "rhinestone-flower", "jelly-flower-lilac", "jelly-star"]


class Scrapbook(Style):
    name = "scrapbook"
    max_w = 860
    line_gap = -8
    word_gap = 0.26
    out_dur = 0.14
    cut_window = (0.0, 0.12)
    push = 0.0

    def __init__(self, ctx):
        self.gem_cache = {}
        super().__init__(ctx)
        self.glint = sparkle(40, WHITE)
        self.flash = Image.new("RGBA", (W, H), (255, 252, 244, 255))
        self.cache = {}
        self.spots = {}

    def grade(self):
        return ("[0:v]eq=contrast=1.04:saturation=1.04:gamma=1.01,"
                "colorbalance=rs=0.03:gs=0.005:bs=-0.02:rh=0.02,vignette=angle=PI/7[bg]")

    def gem_img(self, kind, size):
        key = (kind, int(size))
        if key not in self.gem_cache:
            self.gem_cache[key] = gem(kind, size, seed=len(self.gem_cache))
        return self.gem_cache[key]

    # ---------------------------------------------------------------- captions: mixed type collage
    def word_img(self, text, emph, ci):
        if emph:
            return headline(text.strip(",.!?"), 128)
        return RECIPES[ci % len(RECIPES)](text, 78)

    def animate(self, tk, t, cap, k_out):
        start = self.word_visible_at(tk)
        if t < start:
            return None, 0, 0
        p = prog(t, start, 0.24 if not tk["emph"] else 0.32)
        sc = lerp(0.6 if tk["emph"] else 0.85, 1, out_back(p, 2.2)) * (1 - 0.08 * k_out)
        rot = (1 - out_cubic(p)) * (6 if tk["i"] % 2 else -6)
        return xform(tk["img"], scale=sc, rot=rot, alpha=min(1, p * 4) * (1 - k_out)), 0, 0

    def front(self, canvas, t, cap, lay, cx, cy, k_out):
        """2-3 gems around every caption, popping in one after another, bobbing and glinting."""
        ci = lay["ci"]
        if ci not in self.spots:
            r = np.random.default_rng(ci * 17 + 5)
            w, h = lay["w"], lay["h"]
            side = 1 if ci % 2 else -1
            spots = [(side * (w / 2 + 80), -h / 2 + r.uniform(-20, h * 0.3), 128),
                     (-side * (w / 2 + 66), h / 2 - r.uniform(0, h * 0.4), 100),
                     (side * (w / 2 + 40), h / 2 + 70, 74)]
            if any(tk["emph"] for tk in lay["toks"]) or ci % 3 == 0:
                spots.append((r.uniform(-w / 3, w / 3), -h / 2 - 80, 84))
            kinds = [GEM_ROTATION[(ci * 3 + j) % len(GEM_ROTATION)] for j in range(len(spots))]
            self.spots[ci] = [(x, y, s, k, r.uniform(-20, 20)) for (x, y, s), k in zip(spots, kinds)]
        for j, (x, y, s, kind, rot0) in enumerate(self.spots[ci]):
            p = out_back(prog(t, cap["start"] + 0.07 * (j + 1), 0.32), 2.4)
            if p <= 0:
                continue
            xx = min(max(cx + x, SAFE["left"] + s / 2), SAFE["right"] - s / 2)
            yy = cy + y + 4 * ease_sin(t, 0.45, j * 0.3)
            if self.ctx.hits_face(t, xx, yy, s / 2) or abs(xx - cx) < lay["w"] / 2 and abs(yy - cy) < lay["h"] / 2:
                continue
            img = self.gem_img(kind, s)
            place(canvas, xform(img, scale=p * (1 - 0.3 * k_out), rot=rot0 + 6 * ease_sin(t, 0.3, j * 0.2),
                                alpha=1 - k_out), xx, yy)
            g = (t * 0.8 + j * 0.37 + ci * 0.11) % 1.6          # a glint flashes across each gem now and then
            if g < 0.3 and p >= 1:
                place(canvas, xform(self.glint, scale=math.sin(math.pi * g / 0.3) * s / 70, rot=g * 200,
                                    alpha=1 - k_out), xx + s * 0.22, yy - s * 0.22)

    def ambient(self, canvas, t):
        if "_amb" not in self.__dict__:
            r = np.random.default_rng(77)
            spots = [(r.uniform(70, 150), r.uniform(300, 1400)) for _ in range(4)] + \
                    [(r.uniform(930, 1010), r.uniform(300, 1050)) for _ in range(3)] + \
                    [(r.uniform(200, 880), r.uniform(270, 330)) for _ in range(2)]
            kinds = ["sequin", "chrome-sparkle", "sequin", "jelly-star", "sequin", "gold-star", "jelly-flower-lilac",
                     "sequin", "chrome-star"]
            self._amb = [(x, y, k, r.uniform(44, 62), r.uniform(0, 1)) for (x, y), k in zip(spots, kinds)]
        fade = out_cubic(prog(t, 0.2, 0.8))
        for j, (x, y, kind, s, ph) in enumerate(self._amb):
            yy = y + 6 * ease_sin(t, 0.25, ph)
            if self.ctx.hits_face(t, x, yy, s / 2):
                continue
            place(canvas, xform(self.gem_img(kind, s), alpha=fade, rot=10 * ease_sin(t, 0.15, ph)), x, yy)
            g = (t * 0.5 + ph * 3) % 2.2
            if g < 0.3:
                place(canvas, xform(self.glint, scale=math.sin(math.pi * g / 0.3) * s / 80, rot=g * 200), x + s * 0.2, yy - s * 0.2)

    # ---------------------------------------------------------------- hook: mixed headline + gem shower
    def draw_hook(self, canvas, t, hook):
        if "_hook" not in self.__dict__:
            rows = []
            if hook.get("label"):
                rows.append(yellow_italic(hook["label"], 76))
            words, line, lines = hook["text"].split(), [], []
            for w in words:
                if line and headline(" ".join(line + [w]), 116).width > 920:
                    lines.append(" ".join(line))
                    line = []
                line.append(w)
            lines.append(" ".join(line))
            rows += [headline(ln, 116) for ln in lines]
            if hook.get("sub"):
                rows.append(pink_serif(hook["sub"], 68))
            k = self.ctx.fit(hook["start"], sum(r.height - 2 * r.info["pad"] + 22 for r in rows))
            heights = [(r.height - 2 * r.info["pad"]) * k for r in rows]
            total = sum(heights) + 22 * k * len(rows)
            r = np.random.default_rng(21)
            gems = [(r.uniform(-0.46, 0.46) * W, r.uniform(-0.75, 0.75) * total, GEM_ROTATION[i % len(GEM_ROTATION)],
                     r.uniform(60, 100)) for i in range(7)]
            self._hook = {"rows": rows, "heights": heights, "h": total, "gems": gems, "k": k,
                          "y": self.ctx.block_y(hook["start"], total + 40)}
        hk = self._hook
        local = t - hook["start"]
        k_out = prog(t, hook["end"] - 0.18, 0.18)
        for j, (gx, gy, kind, s) in enumerate(hk["gems"]):
            p = out_back(prog(local, 0.25 + 0.06 * j, 0.32), 2.4)
            if abs(gx) < 300 and abs(gy) < hk["h"] / 2:           # keep the words readable
                gx = math.copysign(330 + s / 2, gx)
            place(canvas, xform(self.gem_img(kind, s), scale=p * (1 - 0.3 * k_out), alpha=1 - k_out,
                                rot=8 * ease_sin(t, 0.3, j * 0.2)), W / 2 + gx, hk["y"] + gy)
        y = hk["y"] - hk["h"] / 2
        for i, (img, h) in enumerate(zip(hk["rows"], hk["heights"])):
            p = prog(local, 0.1 * i, 0.32)
            place(canvas, xform(img, scale=hk["k"] * lerp(0.6, 1, out_back(p, 2.2)) * (1 - 0.08 * k_out),
                                alpha=min(1, p * 4) * (1 - k_out)), W / 2, y + h / 2)
            y += h + 22 * hk["k"]

    # ---------------------------------------------------------------- stickers
    def draw_sticker(self, canvas, t, st):
        """gem (with "kind", see gems.KINDS), star, heart, note ("text" on a taped yellow note),
        photo ("file" relative to the project, shown as a taped print)."""
        kind = st.get("type", "gem")
        key = (kind, st.get("kind"), st.get("text"), st.get("file"))
        if key not in self.cache:
            if kind == "note":
                r = np.random.default_rng(len(st.get("text", "")))
                txt = text_img(st.get("text", "").lower(), HAND, 56, INK, pad=4)
                note = torn_paper(txt.width + 46, txt.height + 26, r, YELLOW)
                note.alpha_composite(txt, ((note.width - txt.width) // 2, (note.height - txt.height) // 2))
                self.cache[key] = note
            elif kind == "photo":
                self.cache[key] = self._photo(st)
            else:
                k = st.get("kind") or {"star": "chrome-star", "heart": "rhinestone-heart"}.get(kind, "gold-star")
                self.cache[key] = self.gem_img(k if k in KINDS else "gold-star", st.get("size", 150))
        img = self.cache[key]
        local = t - st["at"]
        dur = st.get("dur", 1.8)
        p = out_back(prog(local, 0, 0.32), 2.0) * (1 - out_cubic(prog(local, dur - 0.15, 0.15)))
        y = st.get("y", SAFE["top"] + img.height / 2 + 20)
        x = st.get("x", self.ctx.free_x(st["at"], y, img.width)[-1])
        place(canvas, xform(img, scale=p, rot=st.get("rot", -5) + 3 * math.sin(local * 2.5)), x, y)

    def _photo(self, st):
        path = Path(self.ctx.project) / st["file"] if getattr(self.ctx, "project", None) else Path(st["file"])
        r = np.random.default_rng(len(st["file"]))
        im = Image.open(path).convert("RGB")
        w = st.get("w", 380)
        im = im.resize((w, int(im.height * w / im.width)), Image.LANCZOS)
        card = Image.new("RGBA", (im.width + 24, im.height + 24), (252, 250, 245, 255))
        card.paste(im, (12, 12))
        tp = tape(150, 40, r).rotate(r.uniform(-25, 25), expand=True, resample=Image.BICUBIC)
        out = Image.new("RGBA", (card.width, card.height + 30), (0, 0, 0, 0))
        out.alpha_composite(card, (0, 24))
        out.alpha_composite(tp, ((out.width - tp.width) // 2, 0))
        return drop_shadow(out, 0, 6, 8, (30, 20, 10, 110))

    # ---------------------------------------------------------------- transitions
    def draw_cut(self, canvas, t, cut):
        fl = 1 - prog(t, cut, 0.12)
        if fl > 0:
            canvas.alpha_composite(xform(self.flash, alpha=0.5 * fl))

    # ---------------------------------------------------------------- sound
    def sfx(self):
        ev = [(c, "shutter", 0.12) for c in self.ctx.cuts]
        for cap in self.ctx.captions:
            ev.append((cap["start"] + 0.08, "twinkle", 0.06))
            emph = cap.get("emph") or ""
            for w in cap["words"]:
                if emph and _n(w["w"]) == _n(emph):
                    ev.append((w["s"], "pop", 0.2))
        if self.ctx.hook:
            ev.append((self.ctx.hook["start"] + 0.25, "twinkle", 0.18))
        ev += [(st["at"], "pop", 0.18) for st in self.ctx.stickers]
        return ev


def _n(s):
    return "".join(ch for ch in s.lower() if ch.isalnum())


STYLE = Scrapbook
