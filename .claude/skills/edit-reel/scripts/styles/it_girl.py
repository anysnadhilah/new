"""IT GIRL: clean, chic, editorial. Natural bright colour, white classic serif captions with tight tracking shown
a phrase at a time, the key line set big in the middle, soft butter-yellow chapter titles, italic serif labels.
No frames, no flashy transitions: the restraint is the look."""
from common import W
from gfx import deco_star, out_back, out_cubic, place, prog, text_img, xform

INK = "#2B2530"
from styles.base import Style

WHITE = "#FFFFFF"
SERIF = "PlayfairDisplay-Regular.ttf"
ITALIC = "PlayfairDisplay-Italic.ttf"
ACCENT = "#FBD3E0"          # very light pink: key words, chapter titles, stars
SHADOW = (0, 2, 9, (0, 0, 0, 120))
BIG_SHADOW = (0, 3, 14, (90, 30, 60, 150))


def serif(text, size, font=SERIF, fill=WHITE, tracking=-0.045, shadow=SHADOW):
    return text_img(text, font, size, fill, tracking=tracking, shadow=shadow)


class ItGirl(Style):
    name = "it-girl"
    max_w = 820
    line_gap = -6
    word_gap = 0.2
    out_dur = 0.12
    cut_window = (0.0, 0.0)
    cut_punch = 0.02
    push = 0.025

    def grade(self):
        return ("[0:v]eq=contrast=1.03:saturation=0.96:brightness=0.012:gamma=1.01,"
                "colorbalance=rs=0.015:gs=0.005:bs=-0.012:rh=0.01[bg]")

    # ---------------------------------------------------------------- captions: a phrase at a time
    def word_img(self, text, emph, ci):
        if emph:                                                  # the key word: big light pink italic
            return serif(text, 128, ITALIC, fill=ACCENT, tracking=-0.01, shadow=BIG_SHADOW)
        return serif(text, 62, tracking=-0.02)

    def animate(self, tk, t, cap, k_out):
        start = cap["start"]
        p = out_cubic(prog(t, start, 0.28))
        if p <= 0:
            return None, 0, 0
        return xform(tk["img"], alpha=p * (1 - k_out), blur=(1 - p) * 3), 0, (1 - p) * 10

    # ---------------------------------------------------------------- hook: italic kicker, big line, small line
    def draw_hook(self, canvas, t, hook):
        if "_hook" not in self.__dict__:
            times = self.hook_word_times(hook)
            rows, when = [], []
            if hook.get("label"):
                rows.append(serif(hook["label"], 76, ITALIC, tracking=0.0))
                when.append(hook["start"])
            for text, first in self.hook_lines(hook["text"], lambda s: serif(s, 120, tracking=-0.05).width > 900):
                rows.append(serif(text, 120, tracking=-0.05, shadow=BIG_SHADOW))
                when.append(times[first])
            if hook.get("sub"):
                rows.append(serif(hook["sub"], 56))
                when.append(min(hook["end"] - 0.5, when[-1] + 0.5))
            k = self.ctx.fit(hook["start"], sum(r.height - 2 * r.info["pad"] + 26 for r in rows))
            heights = [(r.height - 2 * r.info["pad"]) * k for r in rows]
            total = sum(heights) + 26 * k * len(rows)
            self._hook = {"rows": rows, "when": when, "heights": heights, "h": total, "k": k,
                          "y": self.ctx.block_y(hook["start"], total + 20)}
        hk = self._hook
        k_out = prog(t, hook["end"] - 0.2, 0.2)
        y = hk["y"] - hk["h"] / 2
        for img, h, at in zip(hk["rows"], hk["heights"], hk["when"]):
            p = out_cubic(prog(t, at, 0.4))
            if p > 0:
                place(canvas, xform(img, scale=hk["k"], alpha=p * (1 - k_out), blur=(1 - p) * 4), W / 2, y + h / 2 + (1 - p) * 12)
            y += h + 26 * hk["k"]

    # ---------------------------------------------------------------- stickers
    def draw_sticker(self, canvas, t, st):
        """chapter: light pink italic serif title ("1. hobby journal"); italic: white italic serif label."""
        key = ("st", st.get("type"), st.get("text"))
        if key not in self.__dict__.setdefault("_st", {}):
            text = st.get("text", "")
            if st.get("type") == "chapter":
                img = serif(text, 76, ITALIC, fill=ACCENT, tracking=-0.01, shadow=BIG_SHADOW)
            else:
                img = serif(text, 70, ITALIC, tracking=0.02)
            self._st[key] = img
        img = self._st[key]
        local = t - st["at"]
        dur = st.get("dur", 2.0)
        p = out_cubic(prog(local, 0, 0.3)) * (1 - out_cubic(prog(local, dur - 0.2, 0.2)))
        h = img.height - 2 * img.info["pad"]
        y = st.get("y") or self.clear_y(t, h)
        place(canvas, xform(img, alpha=p), st.get("x", W / 2), y + (1 - p) * 8)

    # ---------------------------------------------------------------- sections: chapter titles
    def draw_section(self, canvas, t):
        """Each new idea opens with a chapter title for 2.6 s: a small italic serif kicker over the point in
        butter-yellow caps, clear of the caption and the face."""
        b = self.beat_at(t)
        if b is None or b["hook"] or t - b["start"] > 2.6:
            return
        key = ("sec", b["i"])
        if key not in self.__dict__.setdefault("_st", {}):
            rows = []
            if b.get("kicker"):
                rows.append(serif(b["kicker"], 54, ITALIC, tracking=0.0))
            for line, _ in self.hook_lines(b["title"], lambda x: serif(x, 96, ITALIC).width > 900):
                rows.append(serif(line, 96, ITALIC, fill=ACCENT, tracking=-0.01, shadow=BIG_SHADOW))
            h = sum(r.height - 2 * r.info["pad"] + 8 for r in rows)
            k, top = self.fit_top(b, h)
            self._st[key] = (rows, k, top)
        rows, k, y = self._st[key]
        local = t - b["start"]
        out = 1 - out_cubic(prog(local, 2.4, 0.2))
        for i, r in enumerate(rows):
            rh = (r.height - 2 * r.info["pad"]) * k
            q = out_cubic(prog(local, 0.08 * i, 0.35))       # rows fade up one after another
            if q > 0:
                place(canvas, xform(r, scale=k, alpha=q * out, blur=(1 - q) * 3), W / 2, y + rh / 2 + (1 - q) * 10)
            y += rh + 8 * k
        widest = max(r.width - 2 * r.info["pad"] for r in rows) * k
        top = self._st[key][2]
        for j, (side, fy, s) in enumerate(((-1, 0.15, 42), (1, 0.75, 34))):    # minimal line stars
            p = out_back(prog(local, 0.35 + 0.12 * j, 0.35), 2.0)
            if p > 0:
                place(canvas, xform(self._star(s), scale=p, alpha=out), W / 2 + side * (widest / 2 + 46), top + fy * (y - top))

    def _star(self, size):
        key = ("star", size)
        if key not in self.__dict__.setdefault("_st", {}):
            kinds = self.ctx.plan.get("star", "burst+spark").split("+")          # "a+b": a for big stars, b for small
            self._st[key] = deco_star(kinds[0] if size >= 38 else kinds[-1], int(size * 1.3), ACCENT)
        return self._st[key]

    def caption_prefer(self, cap):
        return "bottom" if self.heading_on(cap["start"] + 0.01) else None

    def draw_split_title(self, canvas, t):
        """Over a graphic page: the idea as an editorial headline in ink serif (hook words appear as spoken)."""
        b = self.beat_at(t)
        if b is None:
            return
        key = ("split", b["i"])
        if key not in self.__dict__.setdefault("_st", {}):
            kick = serif(b["kicker"], 60, ITALIC, fill=INK, tracking=0.0, shadow=None) if b.get("kicker") else None
            words = b["title"].split()
            imgs = [serif(w, 104, fill=INK, tracking=-0.04, shadow=None) for w in words]
            times = b["times"] or [b["start"] + 0.06 * i for i in range(len(words))]
            rows = []
            for line, first in self.hook_lines(b["title"], lambda x: serif(x, 104, shadow=None).width > 960):
                n = len(line.split())
                rows.append(list(range(first, first + n)))
            self._st[key] = (kick, imgs, times, rows)
        kick, imgs, times, rows = self._st[key]
        k_out = prog(t, b["end"] - 0.16, 0.16)
        if ("fit",) + key not in self.__dict__.setdefault("_fit", {}):
            tot = (kick.height - 2 * kick.info.get("pad", 0) + 6) if kick is not None else 0
            for row in rows:
                ws = [imgs[i].width - 2 * imgs[i].info["pad"] for i in row]
                rh = max(imgs[i].height - 2 * imgs[i].info["pad"] for i in row)
                tot += rh * min(1.0, 960 / (sum(ws) + 22 * (len(row) - 1))) + (-6)
            self._fit[("fit",) + key] = min(1.0, 215 / max(tot, 1))    # fits between Instagram's top bar and the graphic
        fk = self._fit[("fit",) + key]
        y = 195
        if kick is not None:
            kh = kick.height - 2 * kick.info["pad"]
            place(canvas, xform(kick, scale=fk, alpha=out_cubic(prog(t, b["start"], 0.3)) * (1 - k_out)), W / 2, y + kh * fk / 2)
            y += (kh + 6) * fk
        for row in rows:
            ws = [imgs[i].width - 2 * imgs[i].info["pad"] for i in row]
            rh = max(imgs[i].height - 2 * imgs[i].info["pad"] for i in row)
            scale = min(1.0, 960 / (sum(ws) + 22 * (len(row) - 1))) * fk
            x = W / 2 - (sum(ws) + 22 * (len(row) - 1)) * scale / 2
            for i, w in zip(row, ws):
                p = out_cubic(prog(t, times[i], 0.3))
                if p > 0:
                    place(canvas, xform(imgs[i], scale=scale, alpha=p * (1 - k_out), blur=(1 - p) * 3),
                          x + w * scale / 2, y + rh * scale / 2 + (1 - p) * 10)
                x += (w + 22) * scale
            y += rh * scale - 6

    # ---------------------------------------------------------------- sound
    def sfx(self):
        """Clean and light: a zoom on every idea's punch-in, a click as its chapter title lands, a pop per sticker,
        a soft whoosh on the hook."""
        ev = list(self.beat_sfx())
        ev += [(b["start"] + 0.1, "click", 0.16, 2) for b in self.beats() if not b["hook"]]
        ev += [(st["at"], "pop", 0.12, 2) for st in self.ctx.stickers]
        if self.ctx.hook:
            ev.append((self.ctx.hook["start"] + 0.1, "whoosh", 0.08, 3))
        return ev


STYLE = ItGirl
