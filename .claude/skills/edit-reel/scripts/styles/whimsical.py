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

    # ---------------------------------------------------------------- sections: pill + chunky title
    def draw_section(self, canvas, t):
        """Each new idea pops in for 2.6 s: the kicker on a butter pill, the point in chunky two-tone words,
        two twinkling asterisks."""
        b = self.beat_at(t)
        if b is None or b["hook"] or t - b["start"] > 2.6:
            return
        key = ("sec", b["i"])
        if key not in self.cache:
            kick = pill(b["kicker"], fill=BUTTER, size=40) if b.get("kicker") else None
            lines = self.hook_lines(b["title"].lower(), lambda x: chunky(x, 96, CREAM).width > 920)
            rows = [chunky(text, 96, CREAM if i % 2 == 0 else BUTTER) for i, (text, _) in enumerate(lines)]
            h = sum(r.height - 2 * r.info["pad"] - 14 for r in rows) + (kick.height + 8 if kick else 0)
            k, top = self.fit_top(b, h)
            self.cache[key] = (kick, rows, h, k, top)
        kick, rows, h, k, y = self.cache[key]
        local = t - b["start"]
        out = 1 - out_cubic(prog(local, 2.4, 0.2))
        top = y
        if kick is not None:
            p = out_back(prog(local, 0, 0.3), 1.8)
            place(canvas, xform(kick, scale=p * k, alpha=out), W / 2, y + kick.height * k / 2)
            y += (kick.height + 8) * k
        for i, r in enumerate(rows):
            rh = (r.height - 2 * r.info["pad"] - 14) * k
            p = prog(local, 0.12 + 0.1 * i, 0.32)
            if p > 0:
                place(canvas, xform(r, scale=k * lerp(0.7, 1, out_back(p, 1.8)), alpha=min(1, p * 4) * out), W / 2, y + rh / 2)
            y += rh
        for j, (sx, sy, s) in enumerate(((-0.44, 0.1, 64), (0.45, 0.8, 84))):
            p = out_back(prog(local, 0.3 + 0.1 * j, 0.4), 1.8)
            if p > 0:
                place(canvas, xform(self.stars[s], scale=p * k, rot=t * 20, alpha=out), W / 2 + sx * 900, top + sy * h * k)

    def caption_prefer(self, cap):
        return "bottom" if self.heading_on(cap["start"] + 0.01) else None

    def draw_split_title(self, canvas, t):
        """Over a graphic page: the idea in chunky brown and butter words (hook words appear as spoken)."""
        b = self.beat_at(t)
        if b is None:
            return
        key = ("split", b["i"])
        if key not in self.cache:
            kick = pill(b["kicker"], fill=BUTTER, size=40) if b.get("kicker") else None
            words = b["title"].lower().split()
            imgs = [text_img(w, CHUNKY, 92, "#5B3A1A" if i % 2 == 0 else "#E0A400", tracking=-0.03) for i, w in enumerate(words)]
            times = b["times"] or [b["start"] + 0.06 * i for i in range(len(words))]
            rows = [list(range(first, first + len(line.split())))
                    for line, first in self.hook_lines(b["title"].lower(), lambda x: text_img(x, CHUNKY, 92, CREAM).width > 960)]
            self.cache[key] = (kick, imgs, times, rows)
        kick, imgs, times, rows = self.cache[key]
        k_out = prog(t, b["end"] - 0.16, 0.16)
        if ("fit",) + key not in self.__dict__.setdefault("_fit", {}):
            tot = (kick.height - 2 * kick.info.get("pad", 0) + 6) if kick is not None else 0
            for row in rows:
                ws = [imgs[i].width - 2 * imgs[i].info["pad"] for i in row]
                rh = max(imgs[i].height - 2 * imgs[i].info["pad"] for i in row)
                tot += rh * min(1.0, 960 / (sum(ws) + 22 * (len(row) - 1))) + (-4)
            self._fit[("fit",) + key] = min(1.0, 215 / max(tot, 1))    # fits between Instagram's top bar and the graphic
        fk = self._fit[("fit",) + key]
        y = 195
        if kick is not None:
            p = out_back(prog(t, b["start"], 0.3), 1.8)
            place(canvas, xform(kick, scale=p * fk, alpha=1 - k_out), W / 2, y + kick.height * fk / 2)
            y += (kick.height + 6) * fk
        for row in rows:
            ws = [imgs[i].width - 2 * imgs[i].info["pad"] for i in row]
            rh = max(imgs[i].height - 2 * imgs[i].info["pad"] for i in row)
            scale = min(1.0, 960 / (sum(ws) + 22 * (len(row) - 1))) * fk
            x = W / 2 - (sum(ws) + 22 * (len(row) - 1)) * scale / 2
            for i, w in zip(row, ws):
                p = prog(t, times[i], 0.3)
                if p > 0:
                    place(canvas, xform(imgs[i], scale=scale * lerp(0.6, 1, out_back(p, 1.8)), alpha=min(1, p * 3) * (1 - k_out)),
                          x + w * scale / 2, y + rh * scale / 2)
                x += (w + 22) * scale
            y += rh * scale - 4

    # ---------------------------------------------------------------- transitions
    def draw_cut(self, canvas, t, cut):
        fl = 1 - prog(t, cut, 0.12)
        if fl > 0:
            canvas.alpha_composite(xform(self.flash, alpha=0.16 * fl))

    # ---------------------------------------------------------------- sound
    def sfx(self):
        ev = []
        for cap in self.caps:
            emph = cap.get("emph") or ""
            for w in cap["words"]:
                if emph and _n(w["w"]) == _n(emph):
                    ev.append((w["s"], "pop", 0.2))
        if self.ctx.hook:
            ev.append((self.ctx.hook["start"] + 0.1, "twinkle", 0.16, 3))
        ev += [(st["at"], "pop", 0.18, 2) for st in self.ctx.stickers]
        ev += list(self.beat_sfx())                                        # zoom on every idea's punch-in
        for b in self.beats():
            if not b["hook"]:
                ev += [(b["start"] + 0.08, "pop", 0.18, 2), (b["start"] + 0.45, "blob", 0.14, 2)]
        return ev


def _n(s):
    return "".join(ch for ch in s.lower() if ch.isalnum())


STYLE = Whimsical
