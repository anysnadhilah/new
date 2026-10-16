"""IT GIRL: clean, chic, editorial. Natural bright colour, white classic serif captions with tight tracking shown
a phrase at a time, the key line set big in the middle, soft butter-yellow chapter titles, italic serif labels.
No frames, no flashy transitions: the restraint is the look."""
from common import W
from gfx import out_cubic, place, prog, text_img, xform
from styles.base import Style

WHITE = "#FFFFFF"
BUTTER = "#FFF1A6"
SERIF = "Tinos-Regular.ttf"
ITALIC = "Tinos-Italic.ttf"
SANS_BOLD = "Figtree-ExtraBold.ttf"
SHADOW = (0, 2, 9, (0, 0, 0, 120))
BIG_SHADOW = (0, 3, 14, (0, 0, 0, 110))


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
        if emph:
            return serif(text, 132, tracking=-0.05, shadow=BIG_SHADOW)
        return serif(text, 66)

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
        """chapter: bold butter-yellow caps title ("1. HOBBY JOURNAL"); italic: white italic serif label."""
        key = ("st", st.get("type"), st.get("text"))
        if key not in self.__dict__.setdefault("_st", {}):
            text = st.get("text", "")
            if st.get("type") == "chapter":
                img = text_img(text.upper(), SANS_BOLD, 50, BUTTER, tracking=-0.03, shadow=(0, 2, 8, (0, 0, 0, 120)))
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

    # ---------------------------------------------------------------- sound
    def sfx(self):
        ev = [(st["at"], "tick", 0.1) for st in self.ctx.stickers]
        if self.ctx.hook:
            ev.append((self.ctx.hook["start"] + 0.1, "whoosh", 0.08))
        return ev


STYLE = ItGirl
