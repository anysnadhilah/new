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
