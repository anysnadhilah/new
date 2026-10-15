"""WHIMSICAL: dreamy, magical, soft. Pastel glow grade, rounded bubbly words with pastel outlines that
bounce in, a script punch word with floating hearts, twinkling sparkles, drifting bubbles, sparkle bursts on cuts."""
import math

from PIL import Image

from common import H, SAFE, W
from gfx import (heart, lerp, out_back, out_cubic, place, prog, radial, ring, sparkle, star5, text_img, xform)
from styles.base import Style, ease_sin

PASTELS = ["#FF8FC1", "#B49BFF", "#7CCBFF", "#7FD9B2"]
BUTTER = "#FFE27A"
WHITE = "#FFFFFF"
ROUND = "Fredoka-SemiBold.ttf"
SCRIPT = "Pacifico-Regular.ttf"


def shadow_of(col):
    h = col.lstrip("#")
    return (0, 6, 10, (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), 150))


class Whimsical(Style):
    name = "whimsical"
    max_w = 860
    line_gap = 4
    word_gap = 0.3
    out_dur = 0.16
    cut_window = (0.0, 0.6)
    push = 0.0

    def __init__(self, ctx):
        super().__init__(ctx)
        self.sparks = {s: sparkle(s, WHITE) for s in (22, 30, 40, 54)}
        self.butter_spark = sparkle(34, BUTTER)
        self.hearts = {c: heart(40, c, WHITE, 4) for c in PASTELS}
        self.star = star5(70, BUTTER, WHITE, 5)
        self.bubble_imgs = [ring(r, 3, (255, 255, 255, 130)) for r in (14, 20, 26, 34)]
        self.flash = Image.new("RGBA", (W, H), (255, 255, 255, 255))
        haze = radial(270, 480, "#FFC4E4", 0.75, 1.3, alpha=80, invert=True)
        self.static = haze.resize((W, H), Image.BICUBIC)
        r = self.rng
        self.bubbles = [{"x": r.choice([r.uniform(70, 200), r.uniform(880, 1010)]), "speed": r.uniform(35, 70),
                         "phase": r.uniform(0, 1), "img": r.integers(0, 4), "sway": r.uniform(8, 20)} for _ in range(8)]
        self.spark_spots = {}

    def grade(self):
        return ("[0:v]eq=brightness=0.03:contrast=0.93:saturation=0.9:gamma=1.04,"
                "colorbalance=rs=0.04:gs=-0.005:bs=0.05:rh=0.03:bh=0.03,format=gbrp,split[a][b];"
                "[b]gblur=sigma=22[g];[a][g]blend=all_mode=screen:all_opacity=0.16,format=yuv420p[bg]")

    def color(self, ci):
        return PASTELS[ci % len(PASTELS)]

    # ---------------------------------------------------------------- captions
    def word_img(self, text, emph, ci):
        col = self.color(ci)
        if emph:
            return text_img(text.strip(",.!?").lower(), SCRIPT, 104, col, stroke=8, stroke_fill=WHITE,
                            shadow=shadow_of(col))
        return text_img(text.lower(), ROUND, 76, WHITE, stroke=8, stroke_fill=col, shadow=shadow_of(col))

    def animate(self, tk, t, cap, k_out):
        start = self.word_visible_at(tk)
        if t < start:
            return None, 0, 0
        p = prog(t, start, 0.34 if not tk["emph"] else 0.45)
        sc = lerp(0.25, 1.0, out_back(p, 2.2)) * (1 - 0.15 * k_out)
        rot = (1 - out_cubic(p)) * (9 if tk["i"] % 2 else -9)
        dy = (1 - out_cubic(p)) * 28 + 4 * ease_sin(t, 0.6, tk["i"] * 0.27) - 10 * k_out
        return xform(tk["img"], scale=sc, rot=rot, alpha=min(1, p * 3) * (1 - k_out)), 0, dy

    def behind(self, canvas, t, cap, lay, cx, cy, k_out):
        ci = lay["ci"]
        if ci not in self.spark_spots:
            r = self.rng
            w, h = lay["w"], lay["h"]
            self.spark_spots[ci] = [(-w / 2 - 34, -h / 2 + r.uniform(-10, 20), 40),
                                    (w / 2 + 30, r.uniform(-10, h / 2), 30),
                                    (r.uniform(-w / 3, w / 3), -h / 2 - 40, 22)]
        p = out_back(prog(t, cap["start"] + 0.05, 0.35))
        for j, (x, y, s) in enumerate(self.spark_spots[ci]):
            tw = 0.6 + 0.4 * abs(ease_sin(t, 0.9, j * 0.31))
            place(canvas, xform(self.sparks[s], scale=p * tw, rot=t * 40 + j * 30, alpha=1 - k_out), cx + x, cy + y)

    def front(self, canvas, t, cap, lay, cx, cy, k_out):
        for tk in lay["toks"]:
            if not tk["emph"]:
                continue
            for j in range(3):
                local = t - tk["s"] - 0.1 - j * 0.18
                if 0 <= local < 1.2:
                    k = local / 1.2
                    x = cx + tk["x"] + (j - 1) * tk["w"] * 0.35 + 14 * ease_sin(local, 1.2, j * 0.3)
                    y = cy + tk["y"] - tk["h"] * 0.4 - out_cubic(k) * 150
                    place(canvas, xform(self.hearts[self.color(lay["ci"] + j)], scale=0.6 + 0.4 * out_back(min(1, k * 4)),
                                        rot=ease_sin(local, 1.5, j) * 12, alpha=(1 - k) * (1 - k_out)), x, y)

    # ---------------------------------------------------------------- hook
    def draw_hook(self, canvas, t, hook):
        if "_hook" not in self.__dict__:
            lines, cur, cur_w = [], [], 0
            for word in hook["text"].lower().split():
                ims = [text_img(ch, ROUND, 112, WHITE, stroke=10, stroke_fill=PASTELS[0], shadow=shadow_of(PASTELS[0]),
                                pad=40) for ch in word]
                ww = sum(im.width - 80 for im in ims)
                if cur and cur_w + ww + 36 > 880:
                    lines.append(cur)
                    cur, cur_w = [], 0
                cur.append(ims)
                cur_w += ww + 36
            lines.append(cur)
            label = text_img(hook["label"].lower(), SCRIPT, 64, PASTELS[1], stroke=6, stroke_fill=WHITE,
                             shadow=shadow_of(PASTELS[1])) if hook.get("label") else None
            lh = 132
            block_h = lh * len(lines) + (90 if label else 0)
            self._hook = {"lines": lines, "label": label, "lh": lh, "h": block_h,
                          "y": self.ctx.block_y(hook["start"], block_h + 30)}
        hk = self._hook
        local = t - hook["start"]
        k_out = prog(t, hook["end"] - 0.2, 0.2)
        y = hk["y"] - hk["h"] / 2
        if hk["label"] is not None:
            p = out_back(prog(local, 0, 0.4))
            place(canvas, xform(hk["label"], scale=p, rot=-4, alpha=1 - k_out), W / 2, y + 40)
            y += 90
        n = 0
        for line in hk["lines"]:
            lw = sum(sum(im.width - 80 for im in ims) for ims in line) + 36 * (len(line) - 1)
            x = W / 2 - lw / 2
            for ims in line:
                for im in ims:
                    p = prog(local, 0.15 + 0.045 * n, 0.4)
                    w = im.width - 80
                    dy = (1 - out_cubic(p)) * -60 + 5 * ease_sin(t, 0.7, n * 0.2)
                    place(canvas, xform(im, scale=lerp(0.3, 1, out_back(p, 2.4)) * (1 - 0.2 * k_out),
                                        alpha=min(1, p * 3) * (1 - k_out)), x + w / 2, y + hk["lh"] / 2 + dy)
                    x += w
                    n += 1
                x += 36
            y += hk["lh"]
        for j, (sx, sy) in enumerate(((-0.42, -0.1), (0.44, 0.2), (0.3, -0.55), (-0.3, 0.6))):
            p = out_back(prog(local, 0.4 + j * 0.12, 0.4))
            img = self.butter_spark if j % 2 else self.sparks[40]
            place(canvas, xform(img, scale=p * (0.7 + 0.3 * abs(ease_sin(t, 0.8, j * 0.2))), rot=t * 50,
                                alpha=1 - k_out), W / 2 + sx * 900, hk["y"] + sy * hk["h"])

    # ---------------------------------------------------------------- stickers
    def draw_sticker(self, canvas, t, st):
        local = t - st["at"]
        dur = st.get("dur", 1.5)
        p = out_back(prog(local, 0, 0.35), 2.4) * (1 - out_cubic(prog(local, dur - 0.2, 0.2)))
        kind = st.get("type", "heart")
        img = {"heart": self.hearts[PASTELS[0]], "star": self.star, "sparkle": self.sparks[54]}.get(kind, self.star)
        scale = 2.2 if kind == "heart" else 1.0
        y = st.get("y", SAFE["top"] + 160)
        x = st.get("x", self.ctx.free_x(st["at"], y, img.width * scale)[-1])
        place(canvas, xform(img, scale=p * scale, rot=8 * ease_sin(local, 0.8)), x, y + 6 * ease_sin(local, 0.5))

    # ---------------------------------------------------------------- transitions and ambience
    def draw_cut(self, canvas, t, cut):
        k = prog(t, cut, 0.55)
        fl = 1 - prog(t, cut, 0.14)
        if fl > 0:
            canvas.alpha_composite(xform(self.flash, alpha=0.28 * fl))
        cy = self.ctx.block_y(cut + 0.01, 200)
        for j in range(9):
            a = j / 9 * 2 * math.pi + 0.3
            r = lerp(30, 300, out_cubic(k))
            img = self.butter_spark if j % 3 == 0 else self.sparks[30]
            place(canvas, xform(img, scale=1 - k * 0.8, rot=k * 120, alpha=1 - k), W / 2 + r * math.cos(a) * 1.3,
                  cy + r * math.sin(a) * 0.7)

    def ambient(self, canvas, t):
        for b in self.bubbles:
            y = 1500 - ((t * b["speed"] + b["phase"] * 1250) % 1250)
            fade = min(1, (1500 - y) / 120, (y - 250) / 160)
            if fade > 0:
                place(canvas, xform(self.bubble_imgs[b["img"]], alpha=fade * 0.9), b["x"] + b["sway"] * ease_sin(t, 0.25, b["phase"]), y)

    # ---------------------------------------------------------------- sound
    def sfx(self):
        ev = [(c, "twinkle", 0.14) for c in self.ctx.cuts]
        for cap in self.ctx.captions:
            emph = (cap.get("emph") or "")
            for w in cap["words"]:
                if emph and _n(w["w"]) == _n(emph):
                    ev.append((w["s"], "pop", 0.22))
        if self.ctx.hook:
            ev.append((self.ctx.hook["start"] + 0.15, "twinkle", 0.18))
        for st in self.ctx.stickers:
            ev.append((st["at"], "pop", 0.2))
        return ev


def _n(s):
    return "".join(ch for ch in s.lower() if ch.isalnum())


STYLE = Whimsical
