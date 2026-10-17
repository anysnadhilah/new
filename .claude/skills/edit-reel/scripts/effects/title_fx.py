"""19. circle-title: an elegant title above the head, very light pink italic serif (the second line a little softer), a
thin oval in the same colour drawing itself around it like a pen line (its ends leave a small gap at the top) and two minimal line stars
twinkling in beside it (plan.json "star": burst | outline | spark | cross | asterisk | heart). Made for key words: the name of a method, the turn, the takeaway."""
import math

from PIL import Image

from common import H, W
from effects.base import Effect
from gfx import deco_star, out_back, out_cubic, prog, stroke_path, text_img, xform

ITALIC = "PlayfairDisplay-Italic.ttf"
ACCENT = "#FBD3E0"             # very light pink
SOFT_ACCENT = "#F6C2D3"
SHADOW = (0, 3, 10, (110, 40, 70, 150))


class CircleTitle(Effect):
    """Options: text ("line one|line two"), color (very light pink), color2, star, size (150)."""
    name = "circle-title"
    reserves = "top"             # captions move down while it shows
    ease_in = 0.3
    ease_out = 0.25

    def __init__(self, spec, ctx):
        super().__init__(spec, ctx)
        lines = [x for x in spec.get("text", "come back|method").split("|") if x]
        col = spec.get("color", ACCENT)
        self.col = col
        size = int(spec.get("size", 150))
        self.lines = []
        for i, line in enumerate(lines):
            im = text_img(line, ITALIC, size, col if i == 0 else spec.get("color2", SOFT_ACCENT), tracking=-0.01, shadow=SHADOW)
            if i:
                im = xform(im, alpha=0.82)                       # the second line sits a little softer
            self.lines.append(im)
        widest = max(im.width - 2 * im.info["pad"] for im in self.lines)
        self.block_h = sum(im.height - 2 * im.info["pad"] - size * 0.22 for im in self.lines)
        self.rx, self.ry = widest / 2 + 70, self.block_h / 2 + 46
        # fit above the head for every take it spans (it may cover hair / hijab, never the eyes)
        segs = [s for s in ctx.segments if s["start"] < self.end and s["end"] > self.start] or [ctx.seg_at(self.start)]
        brow = min(((s["face"]["cy"] - 0.5 * s["face"]["h"]) * H if s.get("face") else 760) for s in segs)
        full_h = 2 * self.ry + 20
        self.k = max(0.6, min(1.0, (brow - 190) / full_h, 1000 / (2 * self.rx + 60)))
        self.cy = 190 + full_h * self.k / 2
        self._ring = {}
        kinds = (spec.get("star") or (getattr(ctx, "plan", None) or {}).get("star", "burst+spark")).split("+")
        self._stars = [deco_star(kinds[0], 52, col), deco_star(kinds[1 % len(kinds)], 42, col)]   # big, small

    def _oval(self, upto):
        """The oval as a pen stroke from just right of the top centre, round, ending just left of it."""
        q = round(upto * 40) / 40
        if q not in self._ring:
            pts = []
            for i in range(161):
                a = math.radians(-80 + i * (340 / 160))                   # leaves a ~20 degree gap at the top
                wob = 1 + 0.015 * math.sin(a * 3)
                pts.append((self.rx * math.cos(a) * wob, self.ry * math.sin(a) * wob + 0.04 * self.rx * math.cos(a)))
            self._ring[q] = stroke_path(pts, 4, self.col, upto=q)
        return self._ring[q]

    def front(self, frame, t):
        e = self.env(t)
        if e <= 0.01:
            return
        local = t - self.start
        k = self.k
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        y = self.cy - self.block_h * k / 2
        for i, im in enumerate(self.lines):
            h = (im.height - 2 * im.info["pad"] - 150 * 0.22) * k
            p = out_cubic(prog(local, 0.08 + 0.18 * i, 0.4))
            if p > 0:
                img = xform(im, scale=k, alpha=p * e, blur=(1 - p) * 4)
                if img is not None:
                    layer.alpha_composite(img, (int(W / 2 - img.width / 2), int(y + h / 2 - img.height / 2 + (1 - p) * 12)))
            y += h
        d = out_cubic(prog(local, 0.3, 0.7))
        if d > 0:
            ring, (x0, y0) = self._oval(d)
            ring = xform(ring, scale=k, alpha=e)
            if ring is not None:
                cx = W / 2 + x0 * k + ring.width / 2
                cy = self.cy + y0 * k + ring.height / 2
                layer.alpha_composite(ring, (int(cx - ring.width / 2), int(cy - ring.height / 2)))
        for j, (fx, fy, st) in enumerate(((-1.03, -0.62, 0), (1.04, 0.05, 1))):
            p = out_back(prog(local, 0.85 + 0.12 * j, 0.35), 2.0)
            if p > 0:
                tw = 1 + 0.08 * math.sin((local - 0.85) * 5 + j)                # a slow, gentle twinkle
                img = xform(self._stars[st], scale=p * k * tw, alpha=e)
                if img is not None:
                    layer.alpha_composite(img, (int(W / 2 + fx * self.rx * k - img.width / 2),
                                                int(self.cy + fy * self.ry * k - img.height / 2)))
        frame.paste(layer, (0, 0), layer)

    def cues(self):
        return [(self.start + 0.3, "write", 0.1, 2), (self.start + 0.85, "twinkle", 0.14, 2)]


class PeekTitle(Effect):
    """20. peek-title: one big word set just behind the head, so the head only nips the bottom of the letters
    (about a quarter of the small letters) and the word stays readable, like a magazine cover. Playfair italic with a soft pink-to-lilac
    gradient, sliding in from the side; a burst + spark star twinkles in front. Options: text (one or two words),
    colors ([left, right]), overlap (fraction of the small letters the head may cover; default -0.05, the soft edge alone nips them)."""
    name = "peek-title"
    needs_matte = True
    reserves = "top"
    ease_in = 0.4
    ease_out = 0.25

    def __init__(self, spec, ctx):
        super().__init__(spec, ctx)
        import numpy as np
        self.np = np
        text = spec.get("text", "stuck.")
        c0, c1 = spec.get("colors", ["#FCD9E4", "#CDB8F2"])
        size = int(spec.get("size", 260))
        mask = text_img(text, ITALIC, size, "#FFFFFF", tracking=-0.02, pad=10)
        while mask.width > 980 and size > 120:
            size -= 10
            mask = text_img(text, ITALIC, size, "#FFFFFF", tracking=-0.02, pad=10)
        from gfx import rgba
        a, b = np.array(rgba(c0)[:3], np.float32), np.array(rgba(c1)[:3], np.float32)
        ramp = np.linspace(0, 1, mask.width, dtype=np.float32)[None, :, None]
        rgb = (a * (1 - ramp) + b * ramp).repeat(mask.height, axis=0)
        word = Image.fromarray(rgb.astype(np.uint8), "RGB").convert("RGBA")
        word.putalpha(mask.getchannel("A"))
        from gfx import drop_shadow
        self.word = drop_shadow(word, 0, 6, 16, (90, 40, 80, 90))
        box = mask.getchannel("A").getbbox()
        self.ink_top = box[1]
        xbox = text_img("x", ITALIC, size, "#FFFFFF", pad=10).getchannel("A").getbbox()
        self.baseline, self.xh = xbox[3], xbox[3] - xbox[1]          # where letters sit, and their small height
        self.overlap = float(spec.get("overlap", -0.05))       # the soft cutout edge already nips a little
        kinds = (spec.get("star") or (getattr(ctx, "plan", None) or {}).get("star", "burst+spark")).split("+")
        self.stars = [deco_star(kinds[0], 56, c0), deco_star(kinds[-1], 40, c1)]
        self._head = {}

    def _place(self, t):
        """Scale and top-left y so the ink bottom sits `overlap` of the way into the head, never above y=190."""
        # the top of the head on this frame, smoothed so the word glides with her instead of jittering
        if self._head.get("t") != t:
            m = getattr(self, "ctx_matte", None)
            rows = self.np.where((self.np.asarray(m) > 128).sum(axis=1) > 12)[0] if m is not None else []
            f = self.ctx.seg_at(t).get("face")
            now = float(rows[0]) if len(rows) else (((f["cy"] - 1.0 * f["h"]) * H) if f else 420)
            prev = self._head.get("y")
            jump = prev is None or abs(now - prev) > 160 or t - self._head.get("t", -9) > 0.2   # a cut or a seek
            self._head = {"t": t, "y": now if jump else prev * 0.8 + now * 0.2}
        head = self._head["y"]
        # the head may only nip the lowest `overlap` of the small letters: baseline just inside the head
        tall = self.baseline - self.ink_top
        k = max(0.5, min(1.0, (head + self.overlap * self.xh - 190) / tall))
        y = head + self.overlap * self.xh * k - self.baseline * k
        return k, y

    def _draw_word(self, img, t):
        e = self.env(t)
        k, y = self._place(t)
        p = out_cubic(prog(t, self.start, 0.55))
        w = xform(self.word, scale=k, alpha=e * min(1, p * 1.5), blur=(1 - p) * 6)
        if w is not None:
            x = W / 2 - w.width / 2 - (1 - p) * 160
            img.paste(w, (int(x), int(y)), w) if img.mode == "RGB" else img.alpha_composite(w, (int(x), int(y)))
        return k, y

    def behind(self, bg, t):
        self._draw_word(bg, t)

    def front(self, frame, t):
        if getattr(self, "ctx_matte", None) is None:              # no cutout: set it above the head instead
            self._draw_word(frame, t)
        k, y = self._place(t)
        local = t - self.start
        e = self.env(t)
        ww = self.word.width * k
        for j, (fx, fy) in enumerate(((0.47, 0.12), (-0.5, 0.55))):
            p = out_back(prog(local, 0.5 + 0.12 * j, 0.35), 2.0)
            if p > 0:
                tw = 1 + 0.08 * math.sin(local * 5 + j)
                s = xform(self.stars[j], scale=p * tw, alpha=e)
                if s is not None:
                    cx, cy = W / 2 + fx * ww, y + self.ink_top * k + fy * (self.baseline - self.ink_top) * k
                    frame.paste(s, (int(cx - s.width / 2), int(cy - s.height / 2)), s)

    def cues(self):
        return [(self.start, "swish", 0.14, 2), (self.start + 0.5, "blob", 0.14, 2)]
