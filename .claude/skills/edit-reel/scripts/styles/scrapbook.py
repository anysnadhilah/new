"""SCRAPBOOK: a collage journal page come to life, kept calm. One friendly caption treatment (rounded white with
a thin pink edge), the punch word as a pink-glow headline with a single shiny 3D gem beside it, a collage-type
hook that appears line by line with the voice, taped photos and notes as stickers. Nothing blinks or wobbles."""
from pathlib import Path

import numpy as np
from PIL import Image

from common import SAFE, W
from gems import KINDS, gem
from gfx import drop_shadow, lerp, out_back, out_cubic, place, prog, tape, text_img, torn_paper, xform
from styles.base import Style

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


def headline(text, size):
    """Chunky rounded white with a pink outline and pink glow (punch words, the hook)."""
    return text_img(text.lower(), ROUND, size, WHITE, stroke=max(4, size // 18), stroke_fill=HOT_PINK,
                    tracking=-0.02, shadow=(0, 0, size // 7, (238, 95, 167, 200)))


def caption(text, size):
    """Everyday caption words: the same rounded face, small, white with a thin pink edge and a soft shadow."""
    return text_img(text, ROUND, size, WHITE, stroke=3, stroke_fill=HOT_PINK, tracking=-0.01,
                    shadow=(0, 3, 8, (60, 10, 40, 150)))


def pink_serif(text, size):
    return text_img(text, PINK_SERIF, size, PINK, stroke=2, stroke_fill="#B23A78", tracking=-0.03,
                    shadow=(0, 3, 7, (60, 10, 40, 190)))


def yellow_italic(text, size):
    return text_img(text.lower(), ITALIC, size, YELLOW, stroke=max(3, size // 22), stroke_fill=BROWN,
                    tracking=-0.01, shadow=(0, 3, 6, (40, 20, 10, 120)))


GEM_ROTATION = ["rhinestone-heart", "chrome-star", "jelly-flower-pink", "gold-star", "holo-heart",
                "jelly-flower-lilac", "chrome-sparkle", "disco", "rhinestone-flower", "jelly-star"]


class Scrapbook(Style):
    name = "scrapbook"
    max_w = 860
    line_gap = -6
    word_gap = 0.26
    out_dur = 0.14
    cut_window = (0.0, 0.0)
    cut_punch = 0.035
    push = 0.0

    def __init__(self, ctx):
        self.gem_cache = {}
        super().__init__(ctx)
        self.cache = {}

    def grade(self):
        return ("[0:v]eq=contrast=1.03:saturation=1.03:gamma=1.01,"
                "colorbalance=rs=0.025:gs=0.005:bs=-0.015:rh=0.015,vignette=angle=PI/7[bg]")

    def gem_img(self, kind, size):
        key = (kind, int(size))
        if key not in self.gem_cache:
            self.gem_cache[key] = gem(kind, size, seed=len(self.gem_cache))
        return self.gem_cache[key]

    # ---------------------------------------------------------------- captions: calm, one treatment
    def word_img(self, text, emph, ci):
        if emph:
            return headline(text.strip(",.!?"), 120)
        return caption(text.lower(), 70)

    def animate(self, tk, t, cap, k_out):
        start = self.word_visible_at(tk)
        if t < start:
            return None, 0, 0
        p = prog(t, start, 0.18 if not tk["emph"] else 0.28)
        sc = lerp(0.92 if not tk["emph"] else 0.8, 1, out_back(p, 1.6) if tk["emph"] else out_cubic(p))
        return xform(tk["img"], scale=sc * (1 - 0.05 * k_out), alpha=min(1, p * 3) * (1 - k_out)), 0, (1 - out_cubic(p)) * 8

    def front(self, canvas, t, cap, lay, cx, cy, k_out):
        """One gem beside the punch word, appearing with it. Still, no bobbing."""
        emph = [tk for tk in lay["toks"] if tk["emph"]]
        if not emph:
            return
        tk = emph[0]
        ci = lay["ci"]
        side = 1 if ci % 2 else -1
        s = 112
        x = cx + tk["x"] + side * (tk["w"] / 2 + s * 0.55)
        y = cy + tk["y"] - tk["h"] * 0.25
        x = min(max(x, SAFE["left"] + s / 2), SAFE["right"] - s / 2)
        if self.ctx.hits_face(t, x, y, s / 2):
            return
        p = out_back(prog(t, tk["s"] + 0.08, 0.3), 1.8)
        if p <= 0:
            return
        img = self.gem_img(GEM_ROTATION[ci % len(GEM_ROTATION)], s)
        place(canvas, xform(img, scale=p * (1 - 0.3 * k_out), rot=side * -10, alpha=1 - k_out), x, y)

    # ---------------------------------------------------------------- hook: collage type, word by word with the voice
    def draw_hook(self, canvas, t, hook):
        if "_hook" not in self.__dict__:
            times = self.hook_word_times(hook)
            words = hook["text"].split()
            imgs = [headline(w, 116) for w in words]
            gap = 26
            rows = []                                   # each row: list of (word index, image)
            for text, first in self.hook_lines(hook["text"], lambda s: headline(s, 116).width > 920):
                n = len(text.split())
                rows.append([(i, imgs[i]) for i in range(first, first + n)])
            label = yellow_italic(hook["label"], 72) if hook.get("label") else None
            sub = pink_serif(hook["sub"], 64) if hook.get("sub") else None
            pad = imgs[0].info["pad"]
            row_h = max(im.height for im in imgs) - 2 * pad
            heights = ([label.height - 2 * label.info["pad"]] if label else []) + [row_h] * len(rows) + \
                      ([sub.height - 2 * sub.info["pad"]] if sub else [])
            k = self.ctx.fit(hook["start"], sum(h + 22 for h in heights))
            total = sum(h * k + 22 * k for h in heights)
            self._hook = {"rows": rows, "times": times, "label": label, "sub": sub, "row_h": row_h * k, "k": k,
                          "pad": pad, "gap": gap, "h": total, "y": self.ctx.block_y(hook["start"], total + 40)}
        hk = self._hook
        k, k_out = hk["k"], prog(t, hook["end"] - 0.18, 0.18)
        y = hk["y"] - hk["h"] / 2
        if hk["label"] is not None:
            lh = (hk["label"].height - 2 * hk["label"].info["pad"]) * k
            p = out_cubic(prog(t, hook["start"], 0.3))
            place(canvas, xform(hk["label"], scale=k, alpha=p * (1 - k_out)), W / 2, y + lh / 2)
            y += lh + 22 * k
        for row in hk["rows"]:
            widths = [(im.width - 2 * hk["pad"]) * k for _, im in row]
            x = W / 2 - (sum(widths) + hk["gap"] * k * (len(row) - 1)) / 2
            for (i, im), w in zip(row, widths):
                p = prog(t, hk["times"][i], 0.26)
                if p > 0:                               # each word pops in on its own spoken moment
                    place(canvas, xform(im, scale=k * lerp(0.6, 1, out_back(p, 1.8)) * (1 - 0.05 * k_out),
                                        alpha=min(1, p * 3) * (1 - k_out)), x + w / 2, y + hk["row_h"] / 2)
                x += w + hk["gap"] * k
            y += hk["row_h"] + 22 * k
        last = max(hk["times"])
        if hk["sub"] is not None:
            p = out_cubic(prog(t, min(hook["end"] - 0.5, last + 0.35), 0.3))
            sh = (hk["sub"].height - 2 * hk["sub"].info["pad"]) * k
            place(canvas, xform(hk["sub"], scale=k, alpha=p * (1 - k_out)), W / 2, y + sh / 2 + (1 - p) * 10)
        # two gems frame the finished hook
        p = out_back(prog(t, last + 0.15, 0.3), 1.8)
        if p > 0:
            for j, side in enumerate((-1, 1)):
                x = W / 2 + side * min(440, W / 2 - 90)
                gy = hk["y"] - hk["h"] * 0.3 + j * hk["h"] * 0.5
                if not self.ctx.hits_face(t, x, gy, 60):
                    place(canvas, xform(self.gem_img(GEM_ROTATION[j], 104), scale=p, rot=side * -12, alpha=1 - k_out), x, gy)

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
        place(canvas, xform(img, scale=p, rot=st.get("rot", -5)), x, y)          # still: no wobble

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

    # ---------------------------------------------------------------- sound: the hook and the bullet stickers only
    def sfx(self):
        ev = []
        if self.ctx.hook:
            ev.append((self.ctx.hook["start"] + 0.1, "twinkle", 0.14))
        ev += [(st["at"], "pop", 0.14) for st in self.ctx.stickers]
        return ev


def _n(s):
    return "".join(ch for ch in s.lower() if ch.isalnum())


STYLE = Scrapbook
