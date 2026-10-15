"""SCRAPBOOK: crafty, playful, personal. Typewriter words on torn paper strips held by tape, cut-out
ransom-letter punch words, marker doodles that draw themselves, die-cut stickers, torn paper edges,
kraft-paper wipes and camera-shutter flashes on cuts."""
import math

import numpy as np
from PIL import Image

from common import H, SAFE, W
from gfx import (arrow_path, drop_shadow, heart, jagged_poly, lerp, out_back, out_cubic, place, prog, rgba,
                 scribble_circle, squiggle, star5, stroke_path, supersample, tape, text_img, torn_paper, trim,
                 xform)
from styles.base import Style

PAPER = "#FBF5E6"
INK = "#2A2420"
KRAFT = "#C9A27A"
RED, BLUE, YELLOW, GREEN = "#E0453A", "#2F5DA8", "#F4CF4A", "#6DAA6B"
TYPE = "SpecialElite-Regular.ttf"
HAND = "ShadowsIntoLight-Regular.ttf"
RANSOM_FONTS = ["ArchivoBlack-Regular.ttf", "BodoniModa-MediumItalic.ttf", "SpecialElite-Regular.ttf",
                "PermanentMarker-Regular.ttf"]
CHIPS = [(RED, PAPER), (BLUE, PAPER), (YELLOW, INK), (INK, PAPER), (PAPER, INK), (KRAFT, INK), (GREEN, PAPER)]


class Scrapbook(Style):
    name = "scrapbook"
    max_w = 800
    line_gap = 10
    word_gap = 0.32
    out_dur = 0.14
    cut_window = (0.2, 0.25)
    push = 0.0

    def __init__(self, ctx):
        self.ransom = {}
        super().__init__(ctx)
        self.strips, self.doodles, self.doodle_cache = {}, {}, {}
        self.static = self._edges()
        self.sheet = self._kraft_sheet()
        self.flash = Image.new("RGBA", (W, H), (255, 252, 244, 255))
        self.stickers = {"star": star5(110, YELLOW, PAPER, 7), "heart": heart(110, RED, PAPER, 8),
                         "smiley": self._smiley(110)}
        self.wipe_cuts = set(c for i, c in enumerate(ctx.cuts) if i % 3 == 1)

    def grade(self):
        return ("[0:v]eq=contrast=1.04:saturation=0.96:gamma=1.01,"
                "colorbalance=rs=0.035:gs=0.01:bs=-0.035:rh=0.02,vignette=angle=PI/6[bg]")

    # ---------------------------------------------------------------- captions
    def word_img(self, text, emph, ci):
        if emph:
            return self._ransom_word(text.strip(",.!?"), seed=ci * 31 + len(text), size=88)
        return text_img(text.lower(), TYPE, 56, INK, pad=4)

    def _ransom_word(self, word, seed, size):
        r = np.random.default_rng(seed)
        letters, x, hmax = [], 0, 0
        for ch in word:
            if ch == " ":
                x += size * 0.4
                continue
            bg, fg = CHIPS[r.integers(0, len(CHIPS))]
            f = RANSOM_FONTS[r.integers(0, len(RANSOM_FONTS))]
            sz = int(size * r.uniform(0.85, 1.1))
            glyph = trim(text_img(ch.upper() if r.random() < 0.6 else ch.lower(), f, sz, fg, pad=6))
            cw, chh = glyph.width + 20, glyph.height + 18

            def chip(d, k, cw=cw, chh=chh, bg=bg, r=r):
                pts = [(px * k, py * k) for px, py in jagged_poly(cw, chh, r, step=(6, 10), amp=1.6, x0=4, y0=4)]
                d.polygon(pts, fill=rgba(bg))
            card = supersample(cw + 8, chh + 8, chip, k=2)
            card.alpha_composite(glyph, (14, 13))
            card = drop_shadow(card.rotate(r.uniform(-8, 8), resample=Image.BICUBIC, expand=True), 0, 4, 4, (30, 20, 10, 110))
            letters.append([card, x + card.width / 2, r.uniform(-8, 8)])
            x += card.width - 22
            hmax = max(hmax, card.height)
        width = x + 22
        comp = Image.new("RGBA", (int(width) + 2, int(hmax) + 20), (0, 0, 0, 0))
        for card, lx, ly in letters:
            place(comp, card, lx, comp.height / 2 + ly)
        comp.info["pad"] = 0
        self.ransom[id(comp)] = (letters, comp.size)
        return comp

    def animate(self, tk, t, cap, k_out):
        start = self.word_visible_at(tk)
        if t < start:
            return None, 0, 0
        if tk["emph"]:
            letters, size = self.ransom[id(tk["img"])]
            if t > start + 0.05 * len(letters) + 0.3:
                img = tk["img"]
            else:
                img = Image.new("RGBA", size, (0, 0, 0, 0))
                for j, (card, lx, ly) in enumerate(letters):
                    p = prog(t, start + 0.05 * j, 0.22)
                    if p > 0:
                        place(img, xform(card, scale=lerp(1.6, 1, out_back(p, 1.6)), alpha=min(1, p * 4)), lx, size[1] / 2 + ly)
            return xform(img, alpha=1 - k_out), 0, 0
        p = prog(t, start, 0.07)
        return xform(tk["img"], scale=lerp(1.08, 1, p), alpha=p * (1 - k_out)), 0, 0

    def behind(self, canvas, t, cap, lay, cx, cy, k_out):
        """One torn paper strip per typed line (ransom lines float free), slapped down when the caption starts."""
        ci = lay["ci"]
        if ci not in self.strips:
            r = np.random.default_rng(ci * 7 + 3)
            strips = []
            for li, (box, is_ransom) in enumerate(zip(lay["lines"], self._line_kinds(lay))):
                if is_ransom:
                    continue
                x0, y0, x1, y1 = box
                paper = torn_paper(int(x1 - x0 + 56), int(y1 - y0 + 34), r, PAPER if (ci + li) % 3 else "#F3ECFA")
                if li == 0:
                    side = -1 if ci % 2 else 1
                    tp = tape(130, 38, r).rotate(side * r.uniform(18, 30), expand=True, resample=Image.BICUBIC)
                    paper.alpha_composite(tp, (int(paper.width / 2 + side * (paper.width / 2 - 60) - tp.width / 2), 0))
                strips.append((paper, r.uniform(-2.2, 2.2), ((x0 + x1) / 2, (y0 + y1) / 2)))
            self.strips[ci] = strips
        p = prog(t, cap["start"], 0.2)
        for paper, rot, (ox, oy) in self.strips[ci]:
            img = xform(paper, scale=lerp(1.12, 1, out_back(p, 1.4)) * (1 - 0.04 * k_out), rot=rot + (1 - p) * 4,
                        alpha=min(1, p * 5) * (1 - k_out))
            place(canvas, img, cx + ox, cy + oy)

    def _line_kinds(self, lay):
        kinds = []
        for b in lay["lines"]:
            on_line = [tk for tk in lay["toks"] if b[1] <= tk["y"] <= b[3]]
            kinds.append(any(tk["emph"] for tk in on_line))
        return kinds

    def front(self, canvas, t, cap, lay, cx, cy, k_out):
        ci = lay["ci"]
        emph = [tk for tk in lay["toks"] if tk["emph"]]
        if ci not in self.doodles:
            r = np.random.default_rng(ci * 13 + 1)
            if emph:
                tk = emph[0]
                last_line = tk["y"] >= max(b[1] for b in lay["lines"])
                if not last_line:
                    x = tk["x"] + tk["w"] / 2 + 30
                    pts = arrow_path(x + 90, tk["y"] - 70, x, tk["y"], 0.3)
                elif ci % 2:
                    pts = squiggle(tk["x"] - tk["w"] / 2, tk["x"] + tk["w"] / 2, tk["y"] + tk["h"] / 2 + 14, 4, 6)
                else:
                    pts = scribble_circle(tk["x"], tk["y"], tk["w"] / 2 + 34, tk["h"] / 2 + 24, r)
                self.doodles[ci] = (pts, RED if ci % 2 else BLUE, tk["s"] + 0.3)
            elif ci % 3 == 0:
                x = lay["w"] / 2 + 50
                pts = arrow_path(x + 70, -lay["h"] / 2 - 70, x + 4, -6, 0.3)
                self.doodles[ci] = (pts, INK, cap["start"] + 0.2)
            else:
                self.doodles[ci] = None
        d = self.doodles[ci]
        if d is None:
            return
        pts, col, start = d
        p = out_cubic(prog(t, start, 0.4))
        if p <= 0:
            return
        key = (ci, round(p * 16))
        if key not in self.doodle_cache:
            self.doodle_cache[key] = stroke_path(pts, 6, col, upto=round(p * 16) / 16)
        img, (x0, y0) = self.doodle_cache[key]
        place(canvas, xform(img, alpha=1 - k_out), cx + x0 + img.width / 2, cy + y0 + img.height / 2)

    # ---------------------------------------------------------------- hook
    def draw_hook(self, canvas, t, hook):
        if "_hook" not in self.__dict__:
            words = [self._ransom_word(w, seed=97 + i, size=104) for i, w in enumerate(hook["text"].split())]
            lines, cur, cur_w = [], [], 0
            for im in words:
                if cur and cur_w + im.width + 30 > 880:
                    lines.append(cur)
                    cur, cur_w = [], 0
                cur.append(im)
                cur_w += im.width + 30
            lines.append(cur)
            note = None
            if hook.get("label"):
                r = np.random.default_rng(5)
                txt = text_img(hook["label"].lower(), HAND, 58, INK, pad=4)
                note = torn_paper(txt.width + 50, txt.height + 26, r, PAPER)
                note.alpha_composite(txt, ((note.width - txt.width) // 2, (note.height - txt.height) // 2 - 2))
                note.alpha_composite(tape(110, 34, r).rotate(-12, expand=True), (note.width // 2 - 60, -6))
            lh = max(im.height for im in words) + 6
            block_h = lh * len(lines) + (note.height + 20 if note else 0)
            self._hook = {"lines": lines, "note": note, "lh": lh, "h": block_h,
                          "y": self.ctx.block_y(hook["start"], block_h + 30)}
        hk = self._hook
        local = t - hook["start"]
        k_out = prog(t, hook["end"] - 0.15, 0.15)
        y = hk["y"] - hk["h"] / 2
        if hk["note"] is not None:
            p = prog(local, 0, 0.22)
            place(canvas, xform(hk["note"], scale=lerp(1.2, 1, out_back(p)), rot=-3 + (1 - p) * 5,
                                alpha=min(1, p * 5) * (1 - k_out)), W / 2 - 120, y + hk["note"].height / 2)
            y += hk["note"].height + 20
        n = 0
        for line in hk["lines"]:
            lw = sum(im.width for im in line) + 30 * (len(line) - 1)
            x = W / 2 - lw / 2
            for im in line:
                letters, size = self.ransom[id(im)]
                for j, (card, lx, ly) in enumerate(letters):
                    p = prog(local, 0.2 + 0.05 * n, 0.22)
                    if p > 0:
                        place(canvas, xform(card, scale=lerp(1.7, 1, out_back(p, 1.6)), alpha=min(1, p * 4) * (1 - k_out)),
                              x + lx, y + hk["lh"] / 2 + ly)
                    n += 1
                x += im.width + 30
            y += hk["lh"]

    # ---------------------------------------------------------------- stickers
    def draw_sticker(self, canvas, t, st):
        local = t - st["at"]
        dur = st.get("dur", 1.5)
        p = out_back(prog(local, 0, 0.3), 2.2) * (1 - out_cubic(prog(local, dur - 0.15, 0.15)))
        kind = st.get("type", "star")
        if kind == "note":
            if ("note", st.get("text")) not in self.doodle_cache:
                r = np.random.default_rng(len(st.get("text", "")))
                txt = text_img(st.get("text", "").lower(), HAND, 54, INK, pad=4)
                note = torn_paper(txt.width + 44, txt.height + 24, r, YELLOW)
                note.alpha_composite(txt, ((note.width - txt.width) // 2, (note.height - txt.height) // 2))
                self.doodle_cache[("note", st.get("text"))] = note
            img = self.doodle_cache[("note", st.get("text"))]
        else:
            img = drop_shadow(self.stickers.get(kind, self.stickers["star"]), 0, 5, 6, (30, 20, 10, 100))
        y = st.get("y", SAFE["top"] + 150)
        x = st.get("x", self.ctx.free_x(st["at"], y, img.width)[-1])
        place(canvas, xform(img, scale=p, rot=-6 + 4 * math.sin(local * 3)), x, y)

    def _smiley(self, size):
        def draw(d, k):
            s = size * k
            o = 8 * k
            d.ellipse((0, 0, s + 2 * o, s + 2 * o), fill=rgba(PAPER))
            d.ellipse((o, o, s + o, s + o), fill=rgba(YELLOW))
            for ex in (0.36, 0.64):
                d.ellipse(((ex - 0.06) * s + o, 0.3 * s + o, (ex + 0.06) * s + o, 0.46 * s + o), fill=rgba(INK))
            d.arc((0.25 * s + o, 0.3 * s + o, 0.75 * s + o, 0.78 * s + o), 20, 160, fill=rgba(INK), width=int(0.06 * s))
        return supersample(size + 16, size + 16, draw)

    # ---------------------------------------------------------------- transitions and paper edges
    def draw_cut(self, canvas, t, cut):
        if cut in self.wipe_cuts:
            k = prog(t, cut - 0.2, 0.42)
            x = lerp(-self.sheet.width / 2 - 40, W + self.sheet.width / 2 + 40, out_cubic(k) if k < 0.5 else k)
            place(canvas, self.sheet, x, H / 2)
        elif t >= cut:
            fl = 1 - prog(t, cut, 0.12)
            if fl > 0:
                canvas.alpha_composite(xform(self.flash, alpha=0.55 * fl))

    def _kraft_sheet(self):
        r = np.random.default_rng(42)
        w, h = W + 160, H + 160

        def draw(d, k):
            pts = [(x * k, y * k) for x, y in jagged_poly(w - 40, h - 40, r, step=(10, 18), amp=9, x0=20, y0=20)]
            d.polygon(pts, fill=rgba(KRAFT))
        sheet = supersample(w, h, draw, k=1)
        arr = np.asarray(sheet).astype(np.float32)
        arr[..., :3] += r.normal(0, 7, arr.shape[:2])[..., None]
        return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGBA")

    def _edges(self):
        r = np.random.default_rng(9)
        img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        for y0, flip in ((-60, False), (H - 120, True)):
            for col, depth in ((PAPER, 150), (KRAFT, 118)):
                def draw(d, k, depth=depth, col=col):
                    pts = [(x * k, y * k) for x, y in jagged_poly(W + 80, depth, r, step=(9, 16), amp=7, x0=-40, y0=0)]
                    d.polygon(pts, fill=rgba(col))
                band = supersample(W, depth + 20, draw, k=1)
                if flip:
                    band = band.transpose(Image.FLIP_TOP_BOTTOM)
                band = drop_shadow(band, 0, 3 if not flip else -3, 6, (30, 20, 10, 90))
                place(img, band, W / 2, y0 + (depth + 20) / 2 + (30 if not flip else 60))
        return img

    # ---------------------------------------------------------------- sound
    def sfx(self):
        ev = []
        for c in self.ctx.cuts:
            ev.append((c - 0.2, "whoosh", 0.16) if c in self.wipe_cuts else (c, "shutter", 0.14))
        for i, cap in enumerate(self.ctx.captions):
            if i % 2 == 0:
                ev.append((cap["start"], "slap", 0.12))
            emph = cap.get("emph") or ""
            for w in cap["words"]:
                if emph and _n(w["w"]) == _n(emph):
                    for j in range(len(_n(emph))):
                        ev.append((w["s"] - 0.05 + 0.05 * j, "tick", 0.07))
        if self.ctx.hook:
            ev.append((self.ctx.hook["start"], "slap", 0.18))
        for st in self.ctx.stickers:
            ev.append((st["at"], "pop", 0.18))
        return ev


def _n(s):
    return "".join(ch for ch in s.lower() if ch.isalnum())


STYLE = Scrapbook
