"""Shared machinery for every style: reel context, safe zones, face-aware placement, caption layout.

A style subclasses Style and fills in the hooks marked "style hook". render.py calls draw(canvas, t)
once per frame and sfx() once per render.
"""
import math

import numpy as np
from PIL import Image

from common import FPS, H, SAFE, W
from gfx import place, prog


class Context:
    def __init__(self, timeline, plan):
        self.fps = FPS
        self.duration = timeline["duration"]
        self.frames = timeline["frames"]
        self.segments = timeline["segments"]
        self.cuts = [s["start"] for s in self.segments[1:]]
        self.captions = plan.get("captions", [])
        self.hook = plan.get("hook")
        self.stickers = plan.get("stickers", [])
        self.zone_pref = plan.get("zone", "auto")
        if self.zone_pref == "auto":
            self.zone_pref = self._auto_zone()

    def seg_at(self, t):
        for s in self.segments:
            if s["start"] <= t < s["end"]:
                return s
        return self.segments[-1]

    @staticmethod
    def face_px(seg):
        """Head box in output pixels (face detector box grown to cover hair/hijab and chin)."""
        f = seg.get("face")
        if not f:
            return None
        return ((f["cx"] - f["w"] * 0.75) * W, (f["cy"] - f["h"] * 1.05) * H,
                (f["cx"] + f["w"] * 0.75) * W, (f["cy"] + f["h"] * 0.62) * H)

    @staticmethod
    def face_core(seg):
        """Eyes-to-chin box only: text may overlap hair or hijab, never this."""
        f = seg.get("face")
        if not f:
            return None
        return ((f["cx"] - f["w"] * 0.5) * W, (f["cy"] - f["h"] * 0.55) * H,
                (f["cx"] + f["w"] * 0.5) * W, (f["cy"] + f["h"] * 0.6) * H)

    def zones(self, seg, tight=False):
        box = self.face_core(seg) if tight else self.face_px(seg)
        if box is None:
            return {"top": (SAFE["top"], 700), "bottom": (1150, SAFE["bottom"])}
        return {"top": (SAFE["top"], box[1] - 24), "bottom": (box[3] + 24, SAFE["bottom"])}

    def _auto_zone(self):
        score = {"top": 0.0, "bottom": 0.0}
        for s in self.segments:
            for name, (lo, hi) in self.zones(s).items():
                if hi - lo >= 260:
                    score[name] += s["end"] - s["start"]
        return "top" if score["top"] > score["bottom"] else "bottom"

    def block_y(self, t, h, prefer=None):
        """Vertical centre for a block of height h at time t: in a free zone, never on the face.

        Tries the preferred zone, then the other, first keeping clear of the whole head and then only of the
        face itself (eyes to chin); if nothing fits, the roomiest zone, clamped to the safe area."""
        seg = self.seg_at(t)
        first = prefer or self.zone_pref
        order = [first, "bottom" if first == "top" else "top"]
        for tight in (False, True):
            z = self.zones(seg, tight)
            for name in order:
                lo, hi = z[name]
                if hi - lo >= h:
                    if name == "top":
                        return hi - h / 2 if tight else (lo + hi) / 2
                    return lo + h / 2 + (0 if tight else 0.3 * (hi - lo - h))
        z = self.zones(seg, True)
        name = max(z, key=lambda k: z[k][1] - z[k][0])
        lo, hi = z[name]
        y = hi - h / 2 if name == "top" else lo + h / 2
        return min(max(y, SAFE["top"] + h / 2), SAFE["bottom"] - h / 2)

    def free_x(self, t, y, w):
        """Horizontal centre for something w wide at height y that keeps clear of the face."""
        box = self.face_px(self.seg_at(t))
        right = SAFE["right_low"] if y > SAFE["right_low_from"] else SAFE["right"]
        cands = [SAFE["left"] + w / 2 + 10, right - w / 2 - 10]
        if box is None or not (box[1] - w / 2 < y < box[3] + w / 2):
            return cands
        return [x for x in cands if x + w / 2 < box[0] or x - w / 2 > box[2]] or cands


class Style:
    name = "base"
    max_w = 860          # widest caption block
    line_gap = 6
    word_gap = 0.28      # space between words, in em of the word height
    emph_own_line = True
    out_dur = 0.16       # caption exit animation
    cut_window = (0.0, 0.0)  # seconds before/after a cut that draw_cut runs

    def __init__(self, ctx, seed=11):
        self.ctx = ctx
        self.rng = np.random.default_rng(seed)
        self.static = None
        self.layouts = [self.layout(i, c) for i, c in enumerate(ctx.captions)]

    # ------------------------------------------------------------ style hooks
    def grade(self):
        """ffmpeg filter chain from [0:v] to [bg]."""
        return "[0:v]null[bg]"

    def word_img(self, text, emph, ci):
        raise NotImplementedError

    def animate(self, tok, t, cap, k_out):
        """Return (image or None, dx, dy) for one word at time t."""
        raise NotImplementedError

    def behind(self, canvas, t, cap, lay, cx, cy, k_out):
        pass

    def front(self, canvas, t, cap, lay, cx, cy, k_out):
        pass

    def draw_hook(self, canvas, t, hook):
        pass

    def draw_sticker(self, canvas, t, st):
        pass

    def draw_cut(self, canvas, t, cut):
        pass

    def ambient(self, canvas, t):
        pass

    def sfx(self):
        return []

    # ------------------------------------------------------------ layout
    def layout(self, ci, cap):
        emph = (cap.get("emph") or "").lower().strip()
        toks = []
        for wi, w in enumerate(cap["words"]):
            word = w["w"].strip()
            is_emph = bool(emph) and _norm(word) == _norm(emph)
            img = self.word_img(word, is_emph, ci)
            pad = img.info.get("pad", 0)          # transparent margin (shadow room) around the glyphs
            toks.append({"img": img, "w": img.width - 2 * pad, "h": img.height - 2 * pad, "s": w["s"], "e": w["e"],
                         "emph": is_emph, "i": wi, "text": word})
        lines, cur, cur_w = [], [], 0
        for tk in toks:
            gap = tk["h"] * self.word_gap * 0.5 if cur else 0
            force = self.emph_own_line and (tk["emph"] or (cur and cur[-1]["emph"]))
            if cur and (cur_w + gap + tk["w"] > self.max_w or force):
                lines.append(cur)
                cur, cur_w, gap = [], 0, 0
            cur.append(tk)
            cur_w += gap + tk["w"]
        if cur:
            lines.append(cur)
        y = 0
        line_boxes = []
        for ln in lines:
            lh = max(tk["h"] for tk in ln)
            gaps = [tk["h"] * self.word_gap * 0.5 for tk in ln[1:]]
            lw = sum(tk["w"] for tk in ln) + sum(gaps)
            x = -lw / 2
            for j, tk in enumerate(ln):
                tk["x"] = x + tk["w"] / 2
                tk["y"] = y + lh / 2
                x += tk["w"] + (gaps[j] if j < len(gaps) else 0)
            line_boxes.append((-lw / 2, y, lw / 2, y + lh))
            y += lh + self.line_gap
        total_h = y - self.line_gap
        for tk in toks:
            tk["y"] -= total_h / 2
        boxes = [(a, b - total_h / 2, c, d - total_h / 2) for a, b, c, d in line_boxes]
        width = max((b[2] - b[0] for b in boxes), default=0)
        return {"toks": toks, "w": width, "h": total_h, "lines": boxes, "y": None, "ci": ci}

    # ------------------------------------------------------------ frame
    def draw(self, canvas, t):
        if self.static is not None:
            canvas.alpha_composite(self.static)
        self.ambient(canvas, t)
        hook = self.ctx.hook
        in_hook = bool(hook) and hook["start"] <= t < hook["end"]
        for cap, lay in zip(self.ctx.captions, self.layouts):
            if not (cap["start"] <= t < cap["end"]):
                continue
            if in_hook:
                continue        # the hook replaces captions while it is on screen
            if lay["y"] is None:
                lay["y"] = self.ctx.block_y(cap["start"] + 0.01, lay["h"] + 40)
            cx, cy = W / 2, lay["y"]
            k_out = prog(t, cap["end"] - self.out_dur, self.out_dur)
            self.behind(canvas, t, cap, lay, cx, cy, k_out)
            for tk in lay["toks"]:
                img, dx, dy = self.animate(tk, t, cap, k_out)
                place(canvas, img, cx + tk["x"] + dx, cy + tk["y"] + dy)
            self.front(canvas, t, cap, lay, cx, cy, k_out)
        if in_hook:
            self.draw_hook(canvas, t, hook)
        for st in self.ctx.stickers:
            if st["at"] <= t < st["at"] + st.get("dur", 1.5):
                self.draw_sticker(canvas, t, st)
        pre, post = self.cut_window
        for c in self.ctx.cuts:
            if c - pre <= t < c + post:
                self.draw_cut(canvas, t, c)

    def word_visible_at(self, tk):
        return tk["s"] - 0.05


def _norm(s):
    return "".join(ch for ch in s.lower() if ch.isalnum())


def safe_guides(canvas):
    """Red lines marking the Reels safe area (only with --safe)."""
    from PIL import ImageDraw
    d = ImageDraw.Draw(canvas)
    red = (255, 40, 40, 200)
    d.line((0, SAFE["top"], W, SAFE["top"]), fill=red, width=3)
    d.line((0, SAFE["bottom"], W, SAFE["bottom"]), fill=red, width=3)
    d.line((SAFE["left"], 0, SAFE["left"], H), fill=red, width=3)
    d.line((SAFE["right"], 0, SAFE["right"], SAFE["right_low_from"]), fill=red, width=3)
    d.line((SAFE["right_low"], SAFE["right_low_from"], SAFE["right_low"], H), fill=red, width=3)
    d.line((SAFE["right"], SAFE["right_low_from"], SAFE["right_low"], SAFE["right_low_from"]), fill=red, width=3)


def ease_sin(t, speed, phase=0.0):
    return math.sin(2 * math.pi * (t * speed + phase))


def blank():
    return Image.new("RGBA", (W, H), (0, 0, 0, 0))
