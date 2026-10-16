"""SCRAPBOOK: a journal page that talks. The reel is split into sections; each one gets a pinned title at the top
(a handwritten kicker over chunky lavender words, sometimes a pink serif line) that flies together with a sparkle
burst and a magic-glow sound, then stays perfectly still while the speaker explains it. Captions are small and
quiet near the bottom; shiny 3D gems, taped photos, notes and handwritten asides collect around the speaker.

plan.json:
  "hook":     {"text", "label" (kicker), "sub", "start", "end"}   the first title, revealed word by word with the voice
  "sections": [{"start", "end", "kicker", "title", "sub"}]         one pinned title per idea (4 s or longer)
  "stickers": gem | star | heart | note | photo | aside ("text": a handwritten side remark beside the head)
"""
from pathlib import Path

import numpy as np
from PIL import Image

from common import H, SAFE, W
from gems import KINDS, gem
from gfx import drop_shadow, in_out_sine, lerp, out_back, out_cubic, place, prog, sparkle, tape, text_img, torn_paper, xform
from styles.base import Style

LAVENDER = "#F5C6F0"
BUTTER = "#FFF0A0"
CREAM = "#FFF8EC"
PINK = "#F7A6D6"
PLUM = "#4A2A47"
YELLOW = "#F6E27A"
INK = "#2A2420"
CHUNKY = "Fredoka-Bold.ttf"
SCRIPT = "Sacramento-Regular.ttf"
SERIF = "InstrumentSerif-Regular.ttf"
SANS = "Figtree-Medium.ttf"
HAND = "ShadowsIntoLight-Regular.ttf"
SHADOW = (0, 4, 9, (40, 18, 38, 150))
TITLE_TOP = 190          # titles may start here (Instagram's top bar ends above it)
CAPTION_FLOOR = 1565     # captions end above Instagram's caption / username text


def chunky(text, size, fill=LAVENDER):
    return text_img(text.lower(), CHUNKY, size, fill, stroke=max(3, size // 34), stroke_fill=PLUM, tracking=-0.035,
                    shadow=SHADOW)


def script(text, size):
    return text_img(text.lower(), SCRIPT, size, CREAM, stroke=3, stroke_fill=PLUM, shadow=SHADOW)


def serif(text, size, fill=PINK):
    return text_img(text.lower(), SERIF, size, fill, stroke=3, stroke_fill=PLUM, tracking=-0.03, shadow=SHADOW)


def small(text, size, fill="#FFFFFF"):
    return text_img(text.lower(), SANS, size, fill, tracking=0.0, shadow=(0, 2, 6, (0, 0, 0, 190)))


GEM_ROTATION = ["acrylic-star-pink", "acrylic-heart-lilac", "acrylic-star-blue", "acrylic-round-yellow",
                "acrylic-heart-pink", "acrylic-star-lilac", "acrylic-round-blue", "acrylic-star-yellow",
                "acrylic-heart-red", "acrylic-round-pink", "acrylic-star-green", "jelly-flower-pink"]
CONFETTI = ["acrylic-round-pink", "acrylic-star-blue", "acrylic-round-yellow", "acrylic-heart-pink",
            "acrylic-star-lilac", "acrylic-round-clear", "acrylic-round-blue", "acrylic-star-pink",
            "acrylic-round-lilac", "acrylic-heart-red", "acrylic-round-green", "acrylic-star-yellow"]


def _h(im):
    return im.height - 2 * im.info["pad"]


def _w(im):
    return im.width - 2 * im.info["pad"]


class Scrapbook(Style):
    name = "scrapbook"
    max_w = 820
    line_gap = 0
    word_gap = 0.3
    emph_own_line = False
    out_dur = 0.1
    cut_window = (0.0, 0.0)
    cut_punch = 0.03
    push = 0.0
    TITLE = 116          # chunky title size
    ENTER = 0.5          # how long a title takes to fly together

    def on_face(self, t, x, y, r):
        """True if a circle touches the face itself (forehead to chin); hair and hijab are fine to cover."""
        box = self.ctx.face_core(self.ctx.seg_at(t))
        return bool(box) and box[0] - r < x < box[2] + r and box[1] - r < y < box[3] + r

    def __init__(self, ctx):
        self.gem_cache = {}
        super().__init__(ctx)
        self.cache = {}
        self.titles = self._titles()

    def grade(self):
        return ("[0:v]eq=contrast=1.02:saturation=1.04:gamma=1.02,"
                "colorbalance=rs=0.02:gs=0.0:bs=0.01:rh=0.015:bh=0.01[bg]")

    def gem_img(self, kind, size):
        key = (kind, int(size))
        if key not in self.gem_cache:
            self.gem_cache[key] = gem(kind, size, seed=len(self.gem_cache))
        return self.gem_cache[key]

    # ---------------------------------------------------------------- captions: small and quiet, the phrase at once
    def word_img(self, text, emph, ci):
        return small(text, 46, BUTTER if emph else "#FFFFFF")

    def animate(self, tk, t, cap, k_out):
        p = prog(t, cap["start"], 0.12)
        return xform(tk["img"], alpha=p * (1 - k_out)), 0, (1 - out_cubic(p)) * 6

    def caption_y(self, cap, lay):
        """Low and steady like a subtitle (about 78% down the frame, under Instagram's own text line), below the
        chin; the top only when the current title had to sit at the bottom."""
        tt = self.title_at(cap["start"] + 0.01)
        if tt is not None and (tt.get("layout") or self._build(tt))["zone"] == "bottom":
            return self.ctx.block_y(cap["start"] + 0.01, lay["h"] + 40, prefer="top")
        if any(st.get("type") == "aside" and st["at"] < cap["end"] and st["at"] + st.get("dur", 1.8) > cap["start"]
               for st in self.ctx.stickers):
            return CAPTION_FLOOR - lay["h"] / 2          # leave room above for the handwritten aside
        box = self.ctx.face_core(self.ctx.seg_at(cap["start"] + 0.01))
        chin = box[3] if box else 0
        return min(max(1490, chin + 30 + lay["h"] / 2), CAPTION_FLOOR - lay["h"] / 2)

    # ---------------------------------------------------------------- titles
    def _titles(self):
        """The hook and every section become a title: lines of (kind, word images, word start times)."""
        out = []
        hook = self.ctx.hook
        if hook:
            out.append({"start": hook["start"], "end": hook["end"], "kicker": hook.get("label"), "title": hook["text"],
                        "sub": hook.get("sub"), "times": self.hook_word_times(hook), "hook": True})
        for s in self.ctx.plan.get("sections", []) or []:
            if hook and s["start"] < hook["end"] - 0.05:
                continue
            out.append({**s, "times": None, "hook": False})
        for i, tt in enumerate(out):
            tt["i"] = i
        return out

    def _build(self, tt):
        """Lay the title out once: rows of words with sizes, a fit scale for the free room and its height."""
        rows = []
        if tt.get("kicker"):
            rows.append(("kicker", [script(tt["kicker"], 92)], [None]))
        words = tt["title"].split()
        times = tt["times"] or [tt["start"] + 0.05 * i for i in range(len(words))]
        imgs = [chunky(w, self.TITLE) for w in words]
        for text, first in self.hook_lines(tt["title"], lambda s: _w(chunky(s, self.TITLE)) > 900):
            n = len(text.split())
            rows.append(("title", imgs[first:first + n], times[first:first + n]))
        if tt.get("sub"):
            rows.append(("sub", [serif(tt["sub"], 92)], [None]))
        heights = [max(_h(im) for im in ims) * (0.62 if kind == "kicker" else 0.9) for kind, ims, _ in rows]
        total = sum(heights)
        # the title stays for the whole section: fit it above the face in every take it spans
        k = 1.0
        segs = [s for s in self.ctx.segments if s["start"] < tt["end"] and s["end"] > tt["start"]] or [self.ctx.seg_at(tt["start"])]
        # like the references, a title may come down over the hair or hijab to the brows, never onto the eyes
        top_room = min(((s["face"]["cy"] - 0.5 * s["face"]["h"]) * H if s.get("face") else 700) for s in segs) \
            - TITLE_TOP
        zone = "top"
        if top_room < total * 0.5:
            zone = "bottom"
            room = min(SAFE["bottom"] - self.ctx.zones(s, True)["bottom"][0] for s in segs) - 10
            k = max(0.62, min(1.0, room / total))
            y0 = SAFE["bottom"] - total * k
        else:
            k = max(0.62, min(1.0, top_room / total))
            y0 = TITLE_TOP
        rng = np.random.default_rng(tt["i"] + 3)
        widest = max(sum(_w(im) for im in ims) + 0.26 * self.TITLE * (len(ims) - 1) for _, ims, _ in rows) * k
        spots = self._confetti_spots(tt["i"], widest, y0, total * k)
        tt["layout"] = {"rows": rows, "heights": heights, "k": k, "y0": y0, "h": total * k, "zone": zone, "w": widest,
                        "spots": spots,
                        "scatter": [(rng.uniform(-170, 170), rng.uniform(-140, 60), rng.uniform(-28, 28))
                                    for _ in range(len(words) + 2)],
                        "burst": [(rng.uniform(-0.55, 0.55), rng.uniform(-0.2, 1.1), rng.uniform(26, 54), rng.uniform(0, 0.25))
                                  for _ in range(9)]}
        return tt["layout"]

    def title_at(self, t):
        for tt in self.titles:
            if tt["start"] <= t < tt["end"]:
                return tt
        return None

    def draw_title(self, canvas, t, tt):
        lay = tt.get("layout") or self._build(tt)
        k = lay["k"]
        k_out = prog(t, tt["end"] - 0.16, 0.16)
        y = lay["y0"]
        wi = 0
        last_in = tt["start"]
        for (kind, ims, times), h in zip(lay["rows"], lay["heights"]):
            cy = y + h * k / 2
            if kind == "kicker":
                # handwritten: written on from left to right
                im = ims[0]
                p = prog(t, tt["start"], 0.45)
                if p > 0:
                    shown = im.crop((0, 0, max(1, int(im.width * min(1, p * 1.05))), im.height))
                    full = Image.new("RGBA", im.size, (0, 0, 0, 0))
                    full.alpha_composite(shown)
                    full.info["pad"] = im.info["pad"]
                    place(canvas, xform(full, scale=k, alpha=1 - k_out), W / 2, cy)
            elif kind == "sub":
                start = (max(x for x in lay["rows"][-2][2] if x is not None) if tt["hook"] else tt["start"]) + 0.35
                p = out_cubic(prog(t, start, 0.3))
                last_in = max(last_in, start)
                if p > 0:
                    place(canvas, xform(ims[0], scale=k, alpha=p * (1 - k_out)), W / 2, cy + (1 - p) * 14)
            else:
                gap = 0.26 * self.TITLE * k
                widths = [_w(im) * k for im in ims]
                x = W / 2 - (sum(widths) + gap * (len(ims) - 1)) / 2
                for im, w, at in zip(ims, widths, times):
                    dx, dy, rot = lay["scatter"][wi % len(lay["scatter"])]
                    p = prog(t, at, 0.42)
                    last_in = max(last_in, at)
                    if p > 0:               # each word flies in from a scattered spot and settles, then stays still
                        e = out_back(p, 1.5)
                        place(canvas, xform(im, scale=k * lerp(0.35, 1, e) * (1 - 0.04 * k_out), rot=rot * (1 - out_cubic(p)),
                                            alpha=min(1, p * 2.5) * (1 - k_out)),
                              x + w / 2 + dx * (1 - out_cubic(p)), cy + dy * (1 - out_cubic(p)))
                    x += w + gap
                    wi += 1
            y += h * k
        self._decorate(canvas, t, tt, lay, last_in, k_out)

    def _confetti_spots(self, i, w, top, h):
        """Where the acrylic gems settle around a title: both ends of it and a few above / below its corners."""
        rng = np.random.default_rng(40 + i)
        left, right = W / 2 - w / 2, W / 2 + w / 2
        cands = [(left - 52, top + h * 0.35, 92), (right + 52, top + h * 0.6, 84), (left + w * 0.1, top + h + 26, 46),
                 (right - w * 0.12, top - 14, 50), (left - 30, top + h * 0.95, 40), (right + 40, top + h * 0.05, 38),
                 (W / 2 + w * 0.32, top + h + 30, 36)]
        out = []
        for j, (x, y, size) in enumerate(cands):
            x = min(max(x, 70), W - 70)
            out.append((x + rng.uniform(-14, 14), max(y + rng.uniform(-10, 10), 175), int(size * rng.uniform(0.9, 1.15)),
                        CONFETTI[(i * 3 + j) % len(CONFETTI)], rng.uniform(-25, 25)))
        return out

    def _decorate(self, canvas, t, tt, lay, last_in, k_out):
        """While the title lands: a sparkle burst, and acrylic gems burst out from it and settle around it (still)."""
        top, h = lay["y0"], lay["h"]
        for j, (fx, fy, s, delay) in enumerate(lay["burst"]):
            local = t - tt["start"] - delay
            if 0 <= local < 0.9:
                p = np.sin(np.pi * local / 0.9)
                x = W / 2 + fx * 900
                yy = top + fy * h
                if not self.on_face(t, x, yy, s / 2):
                    place(canvas, xform(self._sparkle(int(s)), scale=p, alpha=p * (1 - k_out)), x, yy)
        land = (last_in if tt["hook"] else tt["start"] + 0.12)
        ox, oy = W / 2, top + h / 2
        for j, (x, y, size, kind, rot) in enumerate(lay["spots"]):
            p = prog(t, land + 0.05 * j, 0.42)
            if p <= 0 or self.on_face(t, x, y, size / 2.2):
                continue
            e = out_back(p, 1.6)
            px, py = lerp(ox, x, out_cubic(p)), lerp(oy, y, out_cubic(p)) - 60 * np.sin(np.pi * min(p, 1)) * (1 - p)
            img = self.gem_img(kind, size)
            place(canvas, xform(img, scale=lerp(0.2, 1, e) * (1 - 0.3 * k_out), rot=rot + 140 * (1 - out_cubic(p)),
                                alpha=min(1, p * 3) * (1 - k_out)), px, py)

    # ---------------------------------------------------------------- camera: the zoom rhythm (the visual hook)
    def frame_zoom(self, t):
        """Slow push-in through the hook; every new idea lands with a punch-in and alternates between a wider and
        a closer framing, drifting closer while it is explained; a line with a key word jumps a little closer.
        Always anchored on the eyes, so titles above the head stay clear."""
        seg = self.ctx.seg_at(t)
        f = seg.get("face")
        cx, cy = ((f["cx"] * W, (f["cy"] - 0.2 * f["h"]) * H) if f else (W / 2, H * 0.4))
        tt = self.title_at(t)
        z = 1.0
        if tt is not None and tt["hook"]:
            z = 1 + 0.17 * in_out_sine(prog(t, tt["start"], tt["end"] - tt["start"]))
            last = max(tt["times"] or [tt["start"]])
            z += 0.05 * (1 - out_cubic(prog(t, last, 0.3))) * (t >= last)
        elif tt is not None:
            z = (1.0 if tt["i"] % 2 else 1.09) + 0.04 * prog(t, tt["start"], tt["end"] - tt["start"])
            z += 0.06 * (1 - out_cubic(prog(t, tt["start"], 0.35)))
            for cap in self.caps:
                if cap.get("emph") and cap["start"] <= t < cap["end"]:
                    z += 0.05
                    break
        else:
            z = super().frame_zoom(t)[0]
        return min(z, 1.25), cx, cy

    def _sparkle(self, size):
        key = ("sparkle", size)
        if key not in self.cache:
            self.cache[key] = sparkle(size, "#FFFFFF", glow_blur=max(2, size // 8))
        return self.cache[key]

    def draw_hook(self, canvas, t, hook):
        pass                     # the hook is drawn as the first title (see draw)

    def ambient(self, canvas, t):
        """Draw the title under everything else so captions and stickers sit on top of it."""
        tt = self.title_at(t)
        if tt is None or self.hide_captions:
            return
        lay = tt.get("layout") or self._build(tt)
        if self.reserved and self.reserved == lay["zone"]:
            return
        self.draw_title(canvas, t, tt)
        if tt["hook"]:
            self._intro_gems(canvas, t, tt)

    def _intro_gems(self, canvas, t, tt):
        """The intro collage: three gems pop in one after another around the speaker once the title is said."""
        base = tt["start"] + 0.5
        spots = ((-0.4, 0.47, 140), (0.4, 0.55, 128), (-0.36, 0.66, 104))
        k_out = prog(t, tt["end"] - 0.16, 0.16)
        for j, (fx, fy, s) in enumerate(spots):
            p = out_back(prog(t, base + 0.35 * j, 0.3), 2.0)
            x, y = W / 2 + fx * W, fy * 1920
            if p > 0 and not self.on_face(t, x, y, s / 2.4):
                img = self.gem_img(("acrylic-star-pink", "acrylic-heart-lilac", "acrylic-round-blue")[j], s)
                place(canvas, xform(img, scale=p * (1 - 0.3 * k_out), rot=(-1) ** j * 10, alpha=1 - k_out), x, y)

    # ---------------------------------------------------------------- stickers
    def draw_sticker(self, canvas, t, st):
        """gem (with "kind", see gems.KINDS), star, heart, note ("text" on a taped yellow note),
        photo ("file" relative to the project, shown as a taped print), aside ("text", a handwritten side remark)."""
        kind = st.get("type", "gem")
        key = (kind, st.get("kind"), st.get("text"), st.get("file"))
        if key not in self.cache:
            if kind == "note":
                r = np.random.default_rng(len(st.get("text", "")))
                txt = text_img(st.get("text", "").lower(), HAND, 56, INK, pad=4)
                note = torn_paper(txt.width + 46, txt.height + 26, r, YELLOW)
                note.alpha_composite(txt, ((note.width - txt.width) // 2, (note.height - txt.height) // 2))
                self.cache[key] = note
            elif kind == "aside":
                lines = [serif(x, 60, CREAM) for x in st.get("text", "").split("|")]
                out = Image.new("RGBA", (max(im.width for im in lines), sum(_h(im) for im in lines) + 2 * lines[0].info["pad"]),
                                (0, 0, 0, 0))
                y = 0
                for im in lines:
                    out.alpha_composite(im, ((out.width - im.width) // 2, y))
                    y += _h(im)
                self.cache[key] = out
            elif kind == "photo":
                self.cache[key] = self._photo(st)
            else:
                g = st.get("kind") or {"star": "chrome-star", "heart": "rhinestone-heart"}.get(kind, "gold-star")
                self.cache[key] = self.gem_img(g if g in KINDS else "gold-star", st.get("size", 150))
        img = self.cache[key]
        local = t - st["at"]
        dur = st.get("dur", 1.8)
        p = out_back(prog(local, 0, 0.32), 2.0) * (1 - out_cubic(prog(local, dur - 0.15, 0.15)))
        if "_xy" not in st:                             # decided once, beside the speaker and clear of the words
            if kind == "aside":
                # on the shoulder, just above the (lowered) caption, to one side
                y = st.get("y") or CAPTION_FLOOR - 70 - img.height / 2
                st["_xy"] = (st.get("x") or (SAFE["right_low"] - img.width / 2 if st.get("side", "right") == "right"
                                             else SAFE["left"] + img.width / 2), y)
            else:
                y = st.get("y") or self.clear_y(st["at"], img.height)
                st["_xy"] = (st.get("x") or self.ctx.free_x(st["at"], y, img.width)[-1], y)
        x, y = st["_xy"]
        place(canvas, xform(img, scale=p, rot=st.get("rot", -6 if kind == "aside" else -5)), x, y)

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

    # ---------------------------------------------------------------- sound: a magic glow for every title
    def sfx(self):
        """(time, sound, gain, priority): titles are the moments; the rest only plays on "bold"."""
        ev = []
        for tt in self.titles:
            ev.append((tt["start"], "glow", 0.2, 3 if tt["hook"] else 2))
            if tt.get("kicker"):
                ev.append((tt["start"] + 0.05, "write", 0.08, 0))
        for st in self.ctx.stickers:
            kind = st.get("type", "gem")
            ev.append((st["at"], "write" if kind in ("aside", "note") else "swish", 0.1, 1))
        return ev


STYLE = Scrapbook
