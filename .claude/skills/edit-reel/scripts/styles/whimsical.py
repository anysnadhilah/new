"""WHIMSICAL: cosy, dreamy, playful. Warm creamy glow, chunky lowercase words stacked tight (cream, then butter
yellow), hand-drawn white asterisks that twinkle around them, rounded pill labels for numbers and asides."""
from PIL import Image

from common import SAFE, W
from gfx import asterisk, lerp, out_back, out_cubic, pill, place, prog, star5, text_img, xform
from styles.base import Style, ease_sin

CREAM = "#FFFDF2"
BUTTER = "#FFF0A0"
CHUNKY = "Figtree-ExtraBold.ttf"
SOFT = "Figtree-Medium.ttf"
SHADOW = (0, 4, 14, (70, 45, 20, 120))


def chunky(text, size, fill):
    return text_img(text.lower(), CHUNKY, size, fill, tracking=-0.045, shadow=SHADOW)


class Whimsical(Style):
    name = "whimsical"
    max_w = 880
    line_gap = -18
    word_gap = 0.2
    out_dur = 0.14
    cut_window = (0.0, 0.0)
    cut_punch = 0.03
    push = 0.0

    def __init__(self, ctx):
        super().__init__(ctx)
        self.stars = {s: asterisk(s, arms=4, width=0.13) for s in (46, 64, 84)}
        self.tiny_star = star5(34, CREAM)
        self.flash = Image.new("RGBA", (1080, 1920), (255, 250, 235, 255))
        self.spots = {}
        self.cache = {}

    def grade(self):
        return ("[0:v]eq=brightness=0.025:contrast=0.96:saturation=0.92:gamma=1.03,"
                "colorbalance=rs=0.045:gs=0.02:bs=-0.03:rh=0.03:gh=0.015,format=gbrp,split[a][b];"
                "[b]gblur=sigma=26[g];[a][g]blend=all_mode=screen:all_opacity=0.18,format=yuv420p[bg]")

    # ---------------------------------------------------------------- captions
    def word_img(self, text, emph, ci):
        if emph:
            return chunky(text.strip(",.!?"), 132, BUTTER)
        return chunky(text, 92, CREAM)

    def layout(self, ci, cap):
        lay = super().layout(ci, cap)
        # second line of a plain caption turns butter yellow, like the stacked two-tone headlines
        lines = sorted({round(tk["y"]) for tk in lay["toks"]})
        if len(lines) > 1:
            for tk in lay["toks"]:
                if not tk["emph"] and round(tk["y"]) != lines[0]:
                    tk["img"] = chunky(tk["text"], 92, BUTTER)
        return lay

    def animate(self, tk, t, cap, k_out):
        start = self.word_visible_at(tk)
        if t < start:
            return None, 0, 0
        p = prog(t, start, 0.3)
        sc = lerp(0.7, 1.0, out_back(p, 2.0)) * (1 - 0.1 * k_out)
        dy = (1 - out_cubic(p)) * 18 + 2.5 * ease_sin(t, 0.5, tk["i"] * 0.3)
        return xform(tk["img"], scale=sc, alpha=min(1, p * 4) * (1 - k_out)), 0, dy

    def behind(self, canvas, t, cap, lay, cx, cy, k_out):
        ci = lay["ci"]
        if ci not in self.spots:
            r = self.rng
            w, h = lay["w"], lay["h"]
            side = 1 if ci % 2 else -1
            self.spots[ci] = [(side * (w / 2 + 50), -h / 2 + r.uniform(0, h * 0.4), 64),
                              (-side * (w / 2 + 40), h / 2 - r.uniform(0, h * 0.3), 46)]
            if ci % 3 == 0:
                self.spots[ci].append((r.uniform(-w / 4, w / 4), -h / 2 - 60, 84))
        for j, (x, y, s) in enumerate(self.spots[ci]):
            p = out_back(prog(t, cap["start"] + 0.08 * j, 0.35), 2.2)
            tw = 0.8 + 0.2 * ease_sin(t, 0.7, j * 0.37)
            xx, yy = cx + x, cy + y
            if not SAFE["left"] + s / 2 <= xx <= SAFE["right"] - s / 2:        # no room at the side: go above
                xx, yy = cx + (x / abs(x)) * lay["w"] * 0.3, cy - lay["h"] / 2 - s * 0.7
            if self.ctx.hits_face(t, xx, yy, s / 2):
                continue
            place(canvas, xform(self.stars[s], scale=p * tw, rot=t * 25 * (1 if j % 2 else -1), alpha=1 - k_out), xx, yy)

    # ---------------------------------------------------------------- hook: stacked two-tone headline
    def draw_hook(self, canvas, t, hook):
        if "_hook" not in self.__dict__:
            times = self.hook_word_times(hook)
            lines = self.hook_lines(hook["text"].lower(), lambda s: chunky(s, 150, CREAM).width > 920)
            rows = [chunky(text, 150, CREAM if i % 2 == 0 else BUTTER) for i, (text, _) in enumerate(lines)]
            when = [times[first] for _, first in lines]
            sub = pill(hook["label"], fill=BUTTER, size=40) if hook.get("label") else None
            k = self.ctx.fit(hook["start"], sum(r.height - 2 * r.info["pad"] - 26 for r in rows) + (sub.height + 10 if sub else 0))
            heights = [(r.height - 2 * r.info["pad"] - 26) * k for r in rows]
            total = sum(heights) + (sub.height + 10 if sub else 0)
            self._hook = {"rows": rows, "when": when, "heights": heights, "sub": sub, "h": total, "k": k,
                          "y": self.ctx.block_y(hook["start"], total + 40)}
        hk = self._hook
        k_out = prog(t, hook["end"] - 0.18, 0.18)
        y = hk["y"] - hk["h"] / 2
        for img, h, at in zip(hk["rows"], hk["heights"], hk["when"]):
            p = prog(t, at, 0.35)
            if p > 0:
                place(canvas, xform(img, scale=hk["k"] * lerp(0.7, 1, out_back(p, 1.8)) * (1 - 0.1 * k_out),
                                    alpha=min(1, p * 4) * (1 - k_out)), W / 2, y + h / 2)
            y += h
        last = hk["when"][-1]
        if hk["sub"] is not None:
            p = out_back(prog(t, last + 0.25, 0.35))
            place(canvas, xform(hk["sub"], scale=p, alpha=1 - k_out), W / 2, y + hk["sub"].height / 2 + 10)
        for j, (sx, sy, s) in enumerate(((-0.42, -0.45, 84), (0.43, 0.15, 64))):
            p = out_back(prog(t, last + 0.1 * j, 0.4), 1.8)
            place(canvas, xform(self.stars[s], scale=p, rot=t * 20, alpha=1 - k_out), W / 2 + sx * 900, hk["y"] + sy * hk["h"])

    # ---------------------------------------------------------------- stickers
    def draw_sticker(self, canvas, t, st):
        """pill: white chip ("text", optional "value" on the right); pill-yellow; aside: "(small text)";
        asterisk / star: a big twinkling sparkle."""
        kind = st.get("type", "pill")
        key = (kind, st.get("text"), st.get("value"))
        if key not in self.cache:
            if kind in ("pill", "pill-yellow"):
                self.cache[key] = pill(st.get("text", ""), st.get("value"), fill=BUTTER if kind == "pill-yellow" else "#FFFFFF",
                                       size=42, min_w=560 if st.get("value") else 0)
            elif kind == "aside":
                self.cache[key] = text_img(f"({st.get('text', '')})", SOFT, 44, CREAM, tracking=-0.02, shadow=SHADOW)
            elif kind == "star":
                self.cache[key] = xform(self.tiny_star, scale=2.4)
            else:
                self.cache[key] = self.stars[84]
        img = self.cache[key]
        local = t - st["at"]
        dur = st.get("dur", 2.0)
        p = out_back(prog(local, 0, 0.35), 1.8) * (1 - out_cubic(prog(local, dur - 0.18, 0.18)))
        y = st.get("y") or self.clear_y(t, img.height)
        x = st.get("x", W / 2)
        rot = t * 30 if kind in ("asterisk", "star") else 0
        place(canvas, xform(img, scale=p, rot=rot), x, y + 3 * ease_sin(local, 0.4))

    # ---------------------------------------------------------------- transitions
    def draw_cut(self, canvas, t, cut):
        fl = 1 - prog(t, cut, 0.12)
        if fl > 0:
            canvas.alpha_composite(xform(self.flash, alpha=0.16 * fl))

    # ---------------------------------------------------------------- sound
    def sfx(self):
        ev = []
        for cap in self.ctx.captions:
            emph = cap.get("emph") or ""
            for w in cap["words"]:
                if emph and _n(w["w"]) == _n(emph):
                    ev.append((w["s"], "pop", 0.2))
        if self.ctx.hook:
            ev.append((self.ctx.hook["start"] + 0.1, "twinkle", 0.16))
        ev += [(st["at"], "pop", 0.18) for st in self.ctx.stickers]
        return ev


def _n(s):
    return "".join(ch for ch in s.lower() if ch.isalnum())


STYLE = Whimsical
