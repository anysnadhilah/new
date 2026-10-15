"""IT GIRL: chic, warm, expensive. Creamy film grade, calm lowercase sans + one big italic serif word,
slow push-ins, a hairline that draws itself under the punch word, warm light leaks on cuts."""
import math

from PIL import Image

from common import H, SAFE, W
from gfx import (lerp, out_cubic, out_expo, place, prog, radial, rgba, sparkle, stroke_path, text_img,
                 xform)
from styles.base import Style, ease_sin

CREAM = "#FFF4E6"
BLUSH = "#F4C9C1"
SANS = "Jost-Medium.ttf"
SERIF = "BodoniModa-MediumItalic.ttf"
SOFT_SHADOW = (0, 3, 9, (24, 14, 8, 150))
SERIF_SHADOW = (0, 6, 16, (30, 18, 10, 130))


class ItGirl(Style):
    name = "it-girl"
    max_w = 840
    line_gap = 0
    word_gap = 0.22
    out_dur = 0.2
    cut_window = (0.05, 0.7)
    push = 0.035                     # slow push-in per shot (assemble --push)

    def __init__(self, ctx):
        super().__init__(ctx)
        self.leak = radial(760, 1500, "#FFB27C", 0.0, 1.0, alpha=170)
        self.frame_img = self._frame()
        self.spark = sparkle(30, CREAM)
        self.line_cache = {}

    def grade(self):
        return ("[0:v]eq=contrast=0.95:saturation=0.8:brightness=0.012:gamma=1.03,"
                "colorbalance=rs=0.05:gs=0.015:bs=-0.04:rm=0.035:bm=-0.03:rh=0.02:bh=-0.02,"
                "curves=all='0/0.035 0.5/0.52 1/0.965',vignette=angle=PI/5[bg]")

    # ---------------------------------------------------------------- captions
    def word_img(self, text, emph, ci):
        if emph:
            return text_img(text.lower().strip(",.!?"), SERIF, 132, CREAM, shadow=SERIF_SHADOW)
        return text_img(text.lower(), SANS, 64, CREAM, tracking=0.02, shadow=SOFT_SHADOW)

    def animate(self, tk, t, cap, k_out):
        start = self.word_visible_at(tk)
        if t < start:
            return None, 0, 0
        fade_out = 1 - out_cubic(k_out)
        if tk["emph"]:
            p = out_expo(prog(t, start, 0.55))
            img = self._mask_rise(tk["img"], p)
            return xform(img, alpha=fade_out), 0, -8 * k_out
        p = prog(t, start, 0.38)
        e = out_cubic(p)
        return xform(tk["img"], alpha=min(1, p * 1.6) * fade_out, blur=(1 - e) * 5), 0, (1 - e) * 16 - 8 * k_out

    def _mask_rise(self, img, p):
        """Letters rise into place from behind an invisible baseline."""
        if p >= 0.999:
            return img
        out = Image.new("RGBA", img.size, (0, 0, 0, 0))
        out.alpha_composite(img, (0, int((1 - p) * img.height * 0.85)))
        return out

    def front(self, canvas, t, cap, lay, cx, cy, k_out):
        for tk in lay["toks"]:
            if not tk["emph"]:
                continue
            p = out_cubic(prog(t, tk["s"] + 0.2, 0.5))
            if p <= 0:
                continue
            w = tk["w"] * 0.62
            key = (lay["ci"], round(p * 20))
            if key not in self.line_cache:
                self.line_cache[key] = stroke_path([(0, 0), (w, 0)], 2.2, CREAM, upto=round(p * 20) / 20)
            img, (x0, y0) = self.line_cache[key]
            img = xform(img, alpha=0.85 * (1 - k_out))
            if img is not None:
                place(canvas, img, cx + tk["x"] - w / 2 + x0 + img.width / 2, cy + tk["y"] + tk["h"] * 0.5 + 10 + y0 + img.height / 2)

    # ---------------------------------------------------------------- hook
    def draw_hook(self, canvas, t, hook):
        if "_hook" not in self.__dict__:
            label = text_img((hook.get("label") or "").upper(), SANS, 30, CREAM, tracking=0.32, shadow=SOFT_SHADOW) \
                if hook.get("label") else None
            words = [text_img(w.lower(), SERIF, 124, CREAM, shadow=SERIF_SHADOW) for w in hook["text"].split()]
            lines, cur, cur_w = [], [], 0
            for im in words:
                if cur and cur_w + im.width + 30 > 860:
                    lines.append(cur)
                    cur, cur_w = [], 0
                cur.append(im)
                cur_w += im.width + 30
            lines.append(cur)
            lh = 128
            block_h = (label.height + 40 if label else 0) + lh * len(lines)
            self._hook = {"label": label, "lines": lines, "lh": lh, "h": block_h,
                          "y": self.ctx.block_y(hook["start"], block_h + 30)}
        hk = self._hook
        k_out = prog(t, hook["end"] - 0.25, 0.25)
        fade = 1 - out_cubic(k_out)
        y = hk["y"] - hk["h"] / 2
        local = t - hook["start"]
        if hk["label"] is not None:
            p = out_cubic(prog(local, 0.0, 0.5))
            place(canvas, xform(hk["label"], alpha=p * fade), W / 2, y + hk["label"].height / 2 + (1 - p) * 10)
            for side in (-1, 1):
                sx = W / 2 + side * (hk["label"].width / 2 + 34)
                place(canvas, xform(self.spark, scale=0.7 + 0.25 * ease_sin(t, 0.8, side * 0.25), alpha=p * fade),
                      sx, y + hk["label"].height / 2)
            y += hk["label"].height + 40
        n = 0
        for line in hk["lines"]:
            lw = sum(im.width for im in line) + 30 * (len(line) - 1)
            x = W / 2 - lw / 2
            for im in line:
                p = out_expo(prog(local, 0.25 + 0.09 * n, 0.6))
                place(canvas, xform(self._mask_rise(im, p), alpha=fade), x + im.width / 2, y + hk["lh"] / 2)
                x += im.width + 30
                n += 1
            y += hk["lh"]

    # ---------------------------------------------------------------- stickers
    def draw_sticker(self, canvas, t, st):
        local = t - st["at"]
        dur = st.get("dur", 1.5)
        p = out_cubic(prog(local, 0, 0.35)) * (1 - out_cubic(prog(local, dur - 0.25, 0.25)))
        kind = st.get("type", "sparkle")
        if kind == "label":
            img = text_img(st.get("text", "").upper(), SANS, 30, CREAM, tracking=0.3, shadow=SOFT_SHADOW)
        else:
            img = xform(self.spark, scale=1.3 + 0.3 * ease_sin(t, 0.7))
        x, y = self._spot(st, img)
        place(canvas, xform(img, alpha=p), x, y + (1 - p) * 12)

    def _spot(self, st, img):
        if "x" in st and "y" in st:
            return st["x"], st["y"]
        y = st.get("y", SAFE["top"] + 120)
        return self.ctx.free_x(st["at"], y, img.width)[-1], y

    # ---------------------------------------------------------------- transitions and ambience
    def draw_cut(self, canvas, t, cut):
        k = prog(t, cut - 0.05, 0.75)
        a = math.sin(math.pi * k) * 0.6
        place(canvas, xform(self.leak, alpha=a), lerp(-250, W + 250, in_out(k)), H * 0.42)

    def ambient(self, canvas, t):
        a = out_cubic(prog(t, 0.1, 0.9)) * 0.38
        if a > 0:
            canvas.alpha_composite(self.frame_img if a >= 0.379 else xform(self.frame_img, alpha=a / 0.38))

    def _frame(self):
        from PIL import ImageDraw
        img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(img).rounded_rectangle((34, 34, W - 34, H - 34), radius=26, outline=rgba(CREAM, 97), width=2)
        return img

    # ---------------------------------------------------------------- sound
    def sfx(self):
        ev = [(c - 0.12, "whoosh", 0.10) for c in self.ctx.cuts]
        for cap in self.ctx.captions:
            emph = (cap.get("emph") or "").lower()
            for w in cap["words"]:
                if emph and "".join(ch for ch in w["w"].lower() if ch.isalnum()) == "".join(ch for ch in emph if ch.isalnum()):
                    ev.append((w["s"], "tick", 0.12))
        if self.ctx.hook:
            ev.append((self.ctx.hook["start"] + 0.2, "whoosh", 0.12))
        return ev


def in_out(x):
    return -(math.cos(math.pi * x) - 1) / 2


STYLE = ItGirl
