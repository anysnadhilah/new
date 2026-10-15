"""Whole-frame effects: punch zoom, zoom-through cut, phone frame, pull-back reveal, app split, dolly zoom."""
import math

import cv2
import numpy as np
from PIL import Image, ImageDraw

from common import H, SAFE, W, config
from effects.base import Effect, cover, fast_blur, rounded, zoom, zoom_blur, clips_thumbs
from gfx import asterisk, lerp, out_back, out_cubic, prog, supersample, text_img, xform

CREAM = "#FFFDF2"
BUTTER = "#FFF0A0"
CHUNKY = "Figtree-ExtraBold.ttf"
SOFT = "Figtree-Medium.ttf"


def chunky(text, size, fill):
    return text_img(text.lower(), CHUNKY, size, fill, tracking=-0.045, shadow=(0, 4, 14, (0, 0, 0, 130)))


# ---------------------------------------------------------------- 1. punch zoom (digital zoom)
class PunchZoom(Effect):
    """Fast punch-in on the speaker for a beat, optionally with a big two-tone line ("video|editing")."""
    name = "punch-zoom"
    ease_in = 0.18
    ease_out = 0.2

    def __init__(self, spec, ctx):
        super().__init__(spec, ctx)
        self.amount = float(spec.get("zoom", 1.3)) - 1
        lines = [x for x in spec.get("text", "").split("|") if x]
        self.lines = [chunky(x, 150, CREAM if i % 2 == 0 else BUTTER) for i, x in enumerate(lines)]
        self.hides_captions = bool(lines)

    def whole(self, frame, t):
        cx, cy, top, chin = self.face(t)
        # with words, zoom around a point under the chin: the face rises and the bottom stays free for the text
        ay = min(chin + 260, H - 200) if self.lines else cy
        return zoom(frame, 1 + self.amount * self.env(t), cx, ay)

    def front(self, frame, t):
        if not self.lines:
            return
        hs = [im.height - 2 * im.info["pad"] - 30 for im in self.lines]
        y = SAFE["bottom"] - 40 - sum(hs)              # low: the zoomed-in face fills the middle
        for i, (im, h) in enumerate(zip(self.lines, hs)):
            p = prog(t, self.start + 0.08 + 0.12 * i, 0.3)
            k = 1 - out_cubic(prog(t, self.end - 0.15, 0.15))
            img = xform(im, scale=lerp(0.6, 1, out_back(p, 2)), alpha=min(1, p * 4) * k)
            if img is not None:
                frame.paste(img, (int(W / 2 - img.width / 2), int(y + h / 2 - img.height / 2)), img)
            y += h


# ---------------------------------------------------------------- 2. zoom-through cut
class ZoomThrough(Effect):
    """Transition: rush into the frame with a zoom blur, land in the next shot coming out of the blur.
    "at" = the cut time (defaults to the cut nearest to start)."""
    name = "zoom-through"

    def __init__(self, spec, ctx):
        super().__init__(spec, ctx)
        at = spec.get("at")
        if at is None:
            at = min(ctx.cuts, key=lambda c: abs(c - self.start)) if ctx.cuts else self.start
        self.at = float(at)
        self.half = float(spec.get("half", 0.22))
        self.start, self.end = self.at - self.half, self.at + self.half

    def whole(self, frame, t):
        cx, cy, _, _ = self.face(t)
        if t < self.at:
            p = prog(t, self.start, self.half) ** 2
            out = zoom_blur(frame, 1 + 1.8 * p, p, cx, cy)
        else:
            p = (1 - prog(t, self.at, self.half)) ** 2
            out = zoom_blur(frame, 1 + 1.2 * p, p, cx, cy)
        dark = 1 - 0.35 * math.sin(math.pi * prog(t, self.start, 2 * self.half))
        return Image.fromarray((np.asarray(out) * dark).astype(np.uint8))


# ---------------------------------------------------------------- 3. phone frame (frame break)
class PhoneFrame(Effect):
    """The video shrinks into a phone-screen card with generic reel UI, over a dark blurred copy of itself."""
    name = "phone-frame"
    ease_in = 0.45
    ease_out = 0.35

    def __init__(self, spec, ctx):
        super().__init__(spec, ctx)
        self.scale = float(spec.get("scale", 0.72))
        handle = spec.get("handle") or config().get("instagram") or "yourname"
        self.ui = self._ui(handle)

    def _ui(self, handle):
        w, h = int(W * self.scale), int(H * self.scale)
        ui = Image.new("RGBA", (w, h), (0, 0, 0, 0))

        def icons(d, k):
            x = (w - 60) * k
            r = 26 * k
            for i, kind in enumerate(("heart", "bubble", "plane")):
                y = (h * 0.55 + i * 110) * k
                if kind == "heart":
                    pts = [(x + r * 16 * math.sin(a) ** 3 / 16, y - r * (13 * math.cos(a) - 5 * math.cos(2 * a)
                            - 2 * math.cos(3 * a) - math.cos(4 * a)) / 16) for a in np.linspace(0, 2 * math.pi, 60)]
                    d.line(pts + pts[:1], fill=(255, 255, 255, 235), width=int(5 * k))
                elif kind == "bubble":
                    d.ellipse((x - r, y - r, x + r, y + r), outline=(255, 255, 255, 235), width=int(5 * k))
                else:
                    d.polygon([(x - r, y), (x + r, y - r), (x, y + r)], outline=(255, 255, 255, 235), width=int(5 * k))
        ui = supersample(w, h, icons, k=2)
        name = text_img(f"@{handle}", SOFT, 30, "#FFFFFF", shadow=(0, 2, 6, (0, 0, 0, 140)))
        ui.alpha_composite(name, (24, h - 150))
        btn = text_img("Follow", SOFT, 26, "#FFFFFF")
        bw, bh = btn.width + 26, 46

        def pill(d, k):
            d.rounded_rectangle((0, 0, bw * k - 1, bh * k - 1), radius=12 * k, outline=(255, 255, 255, 230), width=int(2 * k))
        chip = supersample(bw, bh, pill)
        chip.alpha_composite(btn, ((bw - btn.width) // 2, (bh - btn.height) // 2))
        ui.alpha_composite(chip, (name.width + 34, h - 150 + (name.height - bh) // 2))
        return ui

    def whole(self, frame, t):
        e = self.env(t)
        if e <= 0.001:
            return frame
        s = lerp(1.0, self.scale, e)
        back = Image.fromarray((np.asarray(fast_blur(frame, 40)) * lerp(1, 0.45, e)).astype(np.uint8))
        w, h = int(W * s), int(H * s)
        card = rounded(frame.resize((w, h), Image.BILINEAR), int(lerp(0, 46, e)))
        out = back.copy()
        out.paste(card, ((W - w) // 2, (H - h) // 2), card)
        if e > 0.5:
            ui = xform(self.ui, scale=s / self.scale, alpha=(e - 0.5) * 2)
            out.paste(ui, ((W - ui.width) // 2, (H - ui.height) // 2), ui)
        return out


# ---------------------------------------------------------------- 4. pull-back reveal
class PullBack(Effect):
    """Pull back to reveal the video was playing inside an editor window: window chrome, a task list that ticks
    off and a counter that counts up. Options: title, items[], count, label."""
    name = "pull-back"
    hides_captions = True
    ease_in = 0.6
    ease_out = 0.4

    def __init__(self, spec, ctx):
        super().__init__(spec, ctx)
        self.title = spec.get("title", "my-reel.mp4")
        self.items = spec.get("items", ["picked the best takes", "cut the dead air", "captions added", "effects added"])
        self.count = int(spec.get("count", 100))
        self.label = spec.get("label", "frames checked")
        self.paper = Image.new("RGB", (W, H), (244, 241, 234))
        self.bar = text_img(self.title, SOFT, 26, "#555555", pad=2)

    def whole(self, frame, t):
        e = self.env(t)
        if e <= 0.001:
            return frame
        s = lerp(1.0, 0.56, e)
        w, h = int(W * s), int(H * s)
        cx, cy = lerp(W / 2, W * 0.6, e), lerp(H / 2, H * 0.52, e)
        out = Image.blend(frame, self.paper, min(1, e * 1.5)) if e < 0.67 else self.paper.copy()
        win = Image.new("RGBA", (w + 24, h + 70), (255, 255, 255, 255))
        d = ImageDraw.Draw(win)
        for i, col in enumerate(((255, 95, 87), (254, 188, 46), (40, 200, 64))):
            d.ellipse((18 + i * 26, 20, 34 + i * 26, 36), fill=col)
        win.alpha_composite(self.bar, (100, 16))
        win.paste(frame.resize((w, h), Image.BILINEAR), (12, 58))
        win = rounded(win, int(26 * e))
        from gfx import drop_shadow
        win = drop_shadow(win, 0, 14, 22, (60, 40, 20, int(90 * e)))
        place_rgb(out, win, cx, cy)
        if e > 0.6:
            a = (e - 0.6) / 0.4
            local = t - self.start - self.ease_in
            panel = self._panel(local)
            place_rgb(out, xform(panel, alpha=a), W * 0.27, H * 0.47)
            n = int(self.count * out_cubic(prog(local, 0, max(0.5, self.end - self.start - 1.2))))
            num = text_img(f"{n}", CHUNKY, 150, "#1E1E1E", tracking=-0.04)
            lab = text_img(self.label, SOFT, 32, "#6B6B6B")
            place_rgb(out, xform(num, alpha=a), 90 + num.width / 2, SAFE["top"] + 60)
            place_rgb(out, xform(lab, alpha=a), 96 + lab.width / 2, SAFE["top"] + 150)
        return out

    def _panel(self, local):
        w, rows = 420, len(self.items)
        h = 70 + rows * 56
        p = Image.new("RGBA", (w, h), (255, 255, 255, 250))
        d = ImageDraw.Draw(p)
        d.text((22, 18), "working on it", fill=(110, 110, 110), font=_font(SOFT, 24))
        span = max(0.4, self.end - self.start - 1.4) / max(rows, 1)
        for i, item in enumerate(self.items):
            y = 64 + i * 56
            done = local > span * (i + 0.5)
            d.ellipse((22, y, 50, y + 28), fill=(46, 160, 92) if done else None, outline=(46, 160, 92) if done else (190, 190, 190), width=3)
            if done:
                d.line((29, y + 14, 35, y + 20, 44, y + 8), fill="white", width=4)
            d.text((64, y + 1), item, fill=(30, 30, 30) if done else (150, 150, 150), font=_font(SOFT, 24))
        from gfx import drop_shadow
        return drop_shadow(rounded(p, 22), 0, 8, 14, (40, 30, 20, 80))


# ---------------------------------------------------------------- 5. app split (ui world)
class AppSplit(Effect):
    """The video slides down and an app panel fills the top: a drop zone your clips fly into and a prompt that
    types itself. Options: app (name), prompt, images[] (else stills from the reel)."""
    name = "app-split"
    hides_captions = True
    ease_in = 0.45
    ease_out = 0.35

    def __init__(self, spec, ctx):
        super().__init__(spec, ctx)
        self.app = spec.get("app", "studio")
        self.prompt = spec.get("prompt", "edit my reel")
        self.panel_h = int(H * float(spec.get("height", 0.36)))
        imgs = spec.get("images")
        if imgs:
            from effects.base import user_image
            self.thumbs = [cover(user_image(ctx, p), 112, 200) for p in imgs][:5]
        else:
            self.thumbs = clips_thumbs(ctx, 5, (112, 200))

    def whole(self, frame, t):
        e = self.env(t)
        if e <= 0.001:
            return frame
        shift = int(self.panel_h * e)
        out = Image.new("RGB", (W, H), (248, 246, 240))
        out.paste(frame, (0, shift))
        panel = self._panel(t - self.start)
        out.paste(panel, (0, shift - self.panel_h), panel)
        return out

    def _panel(self, local):
        ph = self.panel_h
        p = Image.new("RGBA", (W, ph), (248, 246, 240, 255))
        d = ImageDraw.Draw(p)
        title = text_img(self.app, SOFT, 34, "#463C32", pad=2)
        star = asterisk(30, "#D9774B", arms=4, width=0.16, glow_blur=1)
        p.alpha_composite(star, (int(W / 2 - title.width / 2 - star.width - 4), SAFE["top"] - 72))
        p.alpha_composite(title, (int(W / 2 - title.width / 2 + 10), SAFE["top"] - 68))
        box = (70, SAFE["top"] - 10, W - 70, ph - 40)
        d.rounded_rectangle(box, radius=34, fill=(255, 255, 255), outline=(225, 220, 210), width=3)
        for i, th in enumerate(self.thumbs):
            k = out_back(prog(local, 0.35 + 0.12 * i, 0.4), 1.6)
            if k <= 0:
                continue
            x = 110 + i * 132
            y = box[1] + 30 + (1 - k) * -260
            card = rounded(th, 14)
            p.paste(card, (int(x), int(y)), card)
        typed = self.prompt[: int(max(0, local - 1.0) * 18)]
        caret = "|" if int(local * 2) % 2 == 0 else ""
        d.text((110, box[3] - 70), (typed + caret) or "|", fill=(60, 60, 60), font=_font(SOFT, 34))
        return p


# ---------------------------------------------------------------- 6. dolly zoom (vertigo)
class DollyZoom(Effect):
    """Vertigo: the room zooms while you stay the same size. Options: amount (0.35), direction in|out."""
    name = "dolly-zoom"
    needs_matte = True
    ease_in = 0.2
    ease_out = 0.2

    def background(self, bg, t):
        matte = self.ctx_matte
        if matte is None:
            return bg
        small = np.asarray(bg.resize((W // 4, H // 4), Image.BILINEAR))
        m = np.asarray(matte.resize((W // 4, H // 4), Image.BILINEAR))
        m = cv2.dilate((m > 60).astype(np.uint8) * 255, np.ones((9, 9), np.uint8))
        filled = cv2.inpaint(small, m, 5, cv2.INPAINT_TELEA)
        big = Image.fromarray(cv2.resize(filled, (W, H), interpolation=cv2.INTER_CUBIC))
        sharp = Image.composite(bg, big, Image.fromarray(255 - cv2.resize(m, (W, H))))
        p = prog(t, self.start, self.end - self.start)
        amount = float(self.s.get("amount", 0.35))
        z = 1 + amount * (out_cubic(p) if self.s.get("direction", "in") == "in" else 1 - out_cubic(p))
        cx, cy, _, _ = self.face(t)
        return zoom(sharp, z, cx, cy)


def place_rgb(base, img, cx, cy):
    if img is None:
        return
    x, y = int(cx - img.width / 2), int(cy - img.height / 2)
    base.paste(img, (x, y), img)


def _font(name, size):
    from gfx import font
    return font(name, size)


