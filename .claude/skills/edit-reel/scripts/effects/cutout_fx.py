"""Effects built on the speaker cutout: new background, paper cutout, doodle outline, cover title, glass title."""
import math

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from common import H, SAFE, W
from effects.base import Effect, cover, fast_blur, user_image
from gfx import drop_shadow, out_back, out_cubic, out_expo, prog, rgba, stroke_path, tape, text_img, trim, xform

PAPER = (247, 243, 233)


def paper_texture(seed=3, tint=PAPER):
    r = np.random.default_rng(seed)
    small = r.normal(0, 1, (H // 8, W // 8)).astype(np.float32)
    small = cv2.GaussianBlur(small, (0, 0), 1.2)
    fine = r.normal(0, 4, (H, W)).astype(np.float32)
    base = np.array(tint, np.float32)[None, None, :] + cv2.resize(small, (W, H))[..., None] * 5 + fine[..., None]
    return Image.fromarray(np.clip(base, 0, 255).astype(np.uint8))


# ---------------------------------------------------------------- 12. new background (green screen)
class NewBackground(Effect):
    """Swap the room behind you. Options: image (path in the project), or preset: paper | blur | studio | dark."""
    name = "new-background"
    needs_matte = True

    def __init__(self, spec, ctx):
        super().__init__(spec, ctx)
        if spec.get("image"):
            self.bg = cover(user_image(ctx, spec["image"]))
        else:
            preset = spec.get("preset", "studio")
            if preset == "paper":
                self.bg = paper_texture()
            elif preset == "dark":
                self.bg = Image.new("RGB", (W, H), (18, 18, 20))
            elif preset == "blur":
                self.bg = None
            else:                                                      # soft warm studio sweep
                y, x = np.mgrid[0:H, 0:W].astype(np.float32)
                d = np.sqrt(((x - W / 2) / W) ** 2 + ((y - H * 0.45) / H) ** 2)
                c = np.array([236, 222, 205], np.float32) * (1 - 0.55 * d[..., None])
                self.bg = Image.fromarray(np.clip(c, 0, 255).astype(np.uint8))

    def background(self, bg, t):
        new = self.bg if self.bg is not None else fast_blur(bg, 60)
        e = self.env(t)
        if e >= 0.999:
            return new
        # wipe in from the left, out to the right
        x = int(W * e) if t < self.end - self.ease_out else W
        out = bg.copy()
        if t < self.end - self.ease_out:
            out.paste(new.crop((0, 0, x, H)), (0, 0))
        else:
            k = int(W * (1 - e))
            out.paste(new.crop((k, 0, W, H)), (k, 0))
        return out


# ---------------------------------------------------------------- 13. paper cutout
class PaperCutout(Effect):
    """You become a paper cut-out with a thick white border on a collage page (scribbles, tape, marks,
    cut-out letters). Options: text (cut-out letters, e.g. "100%"), seed."""
    name = "paper-cutout"
    needs_matte = True
    ease_in = 0.15
    ease_out = 0.15

    def __init__(self, spec, ctx):
        super().__init__(spec, ctx)
        self.r = np.random.default_rng(int(spec.get("seed", 8)))
        self.page = self._page()
        self.letters = self._letters(spec.get("text", ""))

    def _page(self):
        page = paper_texture(5).convert("RGBA")
        r = self.r
        d = ImageDraw.Draw(page)
        for i in range(70):                                            # blue pencil scribble block
            y = 300 + i * 9 + r.uniform(-4, 4)
            d.line((470 + r.uniform(-20, 20), y, 1000 + r.uniform(-20, 20), y + r.uniform(-30, 30)),
                   fill=(70, 90, 190, 150), width=3)
        hl = Image.new("RGBA", (520, 300), (250, 226, 60, 200))        # highlighter block
        page.alpha_composite(hl.rotate(-8, expand=True), (500, 820))
        for _ in range(4):                                             # tape
            tp = tape(180, 46, r).rotate(r.uniform(-40, 40), expand=True)
            page.alpha_composite(tp, (int(r.uniform(40, 900)), int(r.uniform(250, 1300))))
        for _ in range(5):                                             # red marks
            x, y = r.uniform(60, 1000), r.uniform(260, 1400)
            d.line((x - 14, y - 14, x + 14, y + 14), fill=(220, 50, 50), width=5)
            d.line((x - 14, y + 14, x + 14, y - 14), fill=(220, 50, 50), width=5)
        for k in range(3):                                             # loops
            x, y = r.uniform(700, 980), r.uniform(1150, 1400)
            pts = [(x + i * 6 + 14 * math.cos(i * 0.9), y + 14 * math.sin(i * 0.9)) for i in range(40)]
            d.line(pts, fill=(30, 30, 30), width=3)
        return page.convert("RGB")

    def _letters(self, text):
        out = []
        fonts = ["Figtree-ExtraBold.ttf", "PlayfairDisplay-SemiBold.ttf", "Nunito-Black.ttf", "Tinos-Regular.ttf"]
        chips = [((30, 70, 170), "white"), ((250, 250, 245), (200, 30, 40)), ((20, 20, 20), "white"),
                 ((250, 250, 245), (20, 20, 20))]
        for i, ch in enumerate(text):
            bg, fg = chips[i % len(chips)]
            g = trim(text_img(ch, fonts[i % len(fonts)], 120, "#%02x%02x%02x" % fg if isinstance(fg, tuple) else fg, pad=6))
            card = Image.new("RGBA", (g.width + 30, g.height + 30), bg + (255,))
            card.alpha_composite(g, (15, 15))
            out.append(drop_shadow(card.rotate(self.r.uniform(-8, 8), expand=True), 0, 6, 6, (0, 0, 0, 90)))
        return out

    def background(self, bg, t):
        return self.page

    def person(self, person, matte, t):
        boil = int(t * 8) % 3                                          # the border wobbles a little, like paper
        m = np.asarray(matte)
        k = 30 + boil * 2
        border = cv2.dilate((m > 100).astype(np.uint8) * 255, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k)))
        border = cv2.GaussianBlur(border, (0, 0), 1.2)
        white = Image.new("RGBA", (W, H), (255, 255, 255, 0))
        white.putalpha(Image.fromarray(border))
        out = drop_shadow(white, 6, 12, 10, (0, 0, 0, 110))
        pad = (out.width - W) // 2
        out = out.crop((pad, pad, pad + W, pad + H))
        out.alpha_composite(person)
        return out

    def front(self, frame, t):
        x = 90
        for i, l in enumerate(self.letters):
            k = out_back(prog(t, self.start + 0.2 + 0.12 * i, 0.3), 2)
            if k > 0:
                img = xform(l, scale=k)
                frame.paste(img, (int(x), int(SAFE["top"] + 40)), img)
            x += l.width - 8


# ---------------------------------------------------------------- 14. doodle outline
DOODLES = {
    "heart": lambda s: [(s * 16 * math.sin(a) ** 3 / 32, -s * (13 * math.cos(a) - 5 * math.cos(2 * a) - 2 * math.cos(3 * a)
                         - math.cos(4 * a)) / 32) for a in np.linspace(0, 2 * math.pi, 40)],
    "star": lambda s: [(s / 2 * (1 if i % 2 == 0 else 0.45) * math.cos(-math.pi / 2 + i * math.pi / 5),
                        s / 2 * (1 if i % 2 == 0 else 0.45) * math.sin(-math.pi / 2 + i * math.pi / 5)) for i in range(11)],
    "sparkle": lambda s: [(0, -s / 2), (s * 0.1, -s * 0.1), (s / 2, 0), (s * 0.1, s * 0.1), (0, s / 2), (-s * 0.1, s * 0.1),
                          (-s / 2, 0), (-s * 0.1, -s * 0.1), (0, -s / 2)],
    "swirl": lambda s: [(s / 2 * (i / 40) * math.cos(i * 0.45), s / 2 * (i / 40) * math.sin(i * 0.45)) for i in range(41)],
    "arrow": lambda s: [(-s / 2, s / 3), (s / 2, -s / 3), (s / 4, -s / 3), (s / 2, -s / 3), (s / 2.4, -s / 9)],
    "clapper": lambda s: [(-s / 2, -s / 6), (s / 2, -s / 6), (s / 2, s / 2), (-s / 2, s / 2), (-s / 2, -s / 6),
                          (-s / 2, -s / 2.2), (s / 2, -s / 2.6), (s / 2, -s / 6)],
}


class DoodleOutline(Effect):
    """A hand-drawn white line traces around you and 'boils' like animation, with little doodles drawn beside your
    head. Options: doodles[] from heart, star, sparkle, swirl, arrow, clapper; color."""
    name = "doodle-outline"
    needs_matte = True
    ease_in = 0.25

    def __init__(self, spec, ctx):
        super().__init__(spec, ctx)
        self.doodles = spec.get("doodles", ["heart", "sparkle", "star"])
        self.color = spec.get("color", "#FFFFFF")
        self.accent = spec.get("accent", "#FF8FC1")

    def front(self, frame, t):
        m = self.ctx_matte
        if m is None:
            return
        e = self.env(t)
        boil = int(t * 8)                                              # redraw jitter 8 times a second
        r = np.random.default_rng(boil)
        small = cv2.resize(np.asarray(m), (W // 4, H // 4))
        cnts, _ = cv2.findContours((small > 110).astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(layer)
        reveal = out_cubic(prog(t, self.start, 0.6))
        for c in cnts:
            if cv2.contourArea(c) < 400:
                continue
            c = cv2.approxPolyDP(c, 1.2, True)[:, 0, :].astype(np.float32) * 4
            c += r.normal(0, 2.2, c.shape)
            n = int(len(c) * reveal)
            if n > 2:
                pts = [tuple(p) for p in c[:n]] + ([tuple(c[0])] if reveal >= 1 else [])
                d.line(pts, fill=rgba(self.color, int(255 * e)), width=7, joint="curve")
        cx, cy, top, chin = self.face(t)
        spots = [(cx - 300, top + 20, 120), (cx + 300, top - 30, 110), (cx + 330, chin + 60, 90), (cx - 330, chin + 90, 90)]
        for i, (kind, (x, y, s)) in enumerate(zip(self.doodles, spots)):
            p = out_cubic(prog(t, self.start + 0.3 + 0.25 * i, 0.5))
            if p <= 0:
                continue
            pts = [(x + px + r.normal(0, 1.5), y + py + r.normal(0, 1.5)) for px, py in DOODLES.get(kind, DOODLES["star"])(s)]
            col = self.accent if kind == "heart" else self.color
            img, (ox, oy) = stroke_path(pts, 6, col, upto=p)
            img = xform(img, alpha=e)
            if img is not None:
                layer.paste(img, (int(ox), int(oy)), img)
        glow = layer.filter(ImageFilter.GaussianBlur(6))
        frame.paste(glow, (0, 0), glow)
        frame.paste(layer, (0, 0), layer)


# ---------------------------------------------------------------- 15. cover title (magazine)
class CoverTitle(Effect):
    """A magazine-cover title set huge behind your head, letters rising into place. Options: text, kicker,
    color."""
    name = "cover-title"
    needs_matte = True
    hides_captions = True

    def __init__(self, spec, ctx):
        super().__init__(spec, ctx)
        text = spec.get("text", "EDIT").upper()
        self.letters = [text_img(ch, "PlayfairDisplay-SemiBold.ttf", 300, spec.get("color", "#FFFFFF"), pad=8,
                                 shadow=(0, 6, 18, (0, 0, 0, 90))) for ch in text]
        total = sum(l.width - 16 for l in self.letters)
        self.k = min(1.0, 960 / max(total, 1))
        self.letters = [xform(l, scale=self.k) for l in self.letters]
        self.kicker = text_img(spec["kicker"].upper(), "Figtree-ExtraBold.ttf", 34, "#FFFFFF", tracking=0.3,
                               shadow=(0, 2, 8, (0, 0, 0, 120))) if spec.get("kicker") else None

    def behind(self, bg, t):
        e = self.env(t)
        cx, cy, top, chin = self.face(t)
        lh = self.letters[0].height
        y = max(SAFE["top"] + lh / 2, top + lh * 0.35)
        x = W / 2 - sum(l.width - 16 * self.k for l in self.letters) / 2
        for i, l in enumerate(self.letters):
            p = out_expo(prog(t, self.start + 0.06 * i, 0.6))
            img = Image.new("RGBA", l.size, (0, 0, 0, 0))
            img.alpha_composite(l, (0, int((1 - p) * l.height * 0.9)))
            img = xform(img, alpha=e)
            if img is not None:
                bg.paste(img, (int(x), int(y - l.height / 2)), img)
            x += l.width - 16 * self.k
        if self.kicker is not None:
            k = xform(self.kicker, alpha=e * out_cubic(prog(t, self.start + 0.4, 0.4)))
            if k is not None:
                bg.paste(k, (int(W / 2 - k.width / 2), int(y - lh / 2 - k.height + 10)), k)

    def front(self, frame, t):
        if self.ctx_matte is None:
            self.behind(frame, t)


# ---------------------------------------------------------------- 16. glass title
class GlassTitle(Effect):
    """A big 3D glass/chrome word stands behind you, letters sliding up into place. Options: text, tint."""
    name = "glass-title"
    needs_matte = True
    hides_captions = True

    def __init__(self, spec, ctx):
        super().__init__(spec, ctx)
        from gems import chrome
        text = spec.get("text", "DESIGN").upper()
        tint = tuple(spec.get("tint", (0.95, 0.95, 1.0)))
        self.letters = []
        for ch in text:
            mask = trim(text_img(ch, "Figtree-ExtraBold.ttf", 280, "#FFFFFF", pad=10))
            size = max(mask.size) + 20
            pts_img = Image.new("L", (size, size), 0)
            pts_img.paste(mask.getchannel("A"), ((size - mask.width) // 2, (size - mask.height) // 2))
            self.letters.append(_shade_mask(pts_img, tint, chrome))
        total = sum(_ink_w(l) for l in self.letters)
        self.k = min(1.0, 980 / max(total, 1))
        self.letters = [xform(l, scale=self.k) for l in self.letters]

    def behind(self, bg, t):
        e = self.env(t)
        cx, cy, top, chin = self.face(t)
        lh = self.letters[0].height
        y = max(SAFE["top"] + lh / 2, top + lh * 0.25)
        widths = [_ink_w(l) for l in self.letters]
        x = W / 2 - sum(widths) / 2
        for i, (l, w) in enumerate(zip(self.letters, widths)):
            p = out_back(prog(t, self.start + 0.07 * i, 0.5), 1.4)
            img = xform(l, alpha=e * min(1, p * 2) * 0.92)
            if img is not None:
                bg.paste(img, (int(x + w / 2 - l.width / 2), int(y - l.height / 2 + (1 - p) * 140)), img)
            x += w

    def front(self, frame, t):
        if self.ctx_matte is None:
            self.behind(frame, t)


def _ink_w(img):
    box = img.getchannel("A").point(lambda v: 255 if v > 40 else 0).getbbox()
    return (box[2] - box[0]) * 0.96 if box else img.width


def _shade_mask(mask_img, tint, chrome):
    """Light a letter-shaped mask with the gem renderer's chrome material."""
    import gems
    size = mask_img.width
    m = np.asarray(mask_img.resize((size * gems.K, size * gems.K), Image.LANCZOS), np.float32) / 255
    n, _ = gems._normals(m, 1.0, 0.7)
    diffuse, spec = gems._shade(n)
    ny = n[..., 1]
    env = 0.62 + 0.38 * np.tanh(-ny * 5) - 0.42 * np.exp(-((ny - 0.12) * 9) ** 2) + 0.18 * n[..., 0]
    v = np.clip(env * 0.75 + diffuse * 0.35, 0, 1)[..., None] * np.array(tint) + (spec ** 60)[..., None] * 1.2
    return gems._finish(v, m, size)

