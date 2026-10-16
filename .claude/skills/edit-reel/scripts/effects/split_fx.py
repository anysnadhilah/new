"""18. split-panel: the clip is pushed down into a card and a motion graphic plays in the space above it, so a
graphic never hides behind (or covers) the speaker's head. Panels:

  calendar    a calendar app; events pop onto their days one by one with a cursor click
  popups      retro pop-up windows pile up (overwhelm, "too many things"): great as an intro hook
  todo-scroll a never-ending to-do list scrolls past with a growing counter
  time-bars   free hours per day grow as bars and a total counts up
  goals       goal cards pop in, then only the chosen ones stay lit and get a check

Every panel also reports its sound cues (zoom on the push, clicks / pops / blobs on its beats).
"""
import calendar as cal
import datetime

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from common import H, W
from effects.base import Effect, rounded
from gfx import drop_shadow, font, lerp, out_back, out_cubic, prog, rgba, text_img, xform

CARD_SCALE = 0.5
CARD_TOP = 945                  # the pushed-down clip: 540 x 960 from here down
PANEL_BOTTOM = 925
UI = "Figtree-Medium.ttf"
UI_BOLD = "Figtree-ExtraBold.ttf"
CHUNKY = "Fredoka-Bold.ttf"
SCRIPT = "Sacramento-Regular.ttf"
PLUM = "#4A2A47"
INK = "#2B2530"
PASTELS = ["#C9B6F5", "#F7A6D6", "#9FD3F5", "#FFE07A", "#A8E6B0", "#FFB38A"]


def _put(base, img, cx, cy):
    if img is None:                                   # fully transparent / zero size this frame
        return
    base.alpha_composite(img, (int(cx - img.width / 2), int(cy - img.height / 2)))


def _cursor(size=46):
    s = size
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    pts = [(4, 2), (4, s * 0.78), (s * 0.3, s * 0.6), (s * 0.48, s * 0.95), (s * 0.6, s * 0.9), (s * 0.43, s * 0.56),
           (s * 0.72, s * 0.56)]
    d.polygon(pts, fill=(255, 255, 255, 255), outline=(20, 20, 20, 255))
    d.line(pts + [pts[0]], fill=(20, 20, 20, 255), width=3)
    return img


class SplitPanel(Effect):
    """The clip slides down into a card on a striped page; a motion graphic fills the space above it.
    Options: panel (calendar | popups | todo-scroll | time-bars | goals), title (heading, drawn by the effect only
    when the style has no pinned title of its own) and the panel's own data (see references/effects.md)."""
    name = "split-panel"
    hides_captions = True
    keeps_title = True           # scrapbook keeps its pinned title, set small at the very top
    ease_in = 0.45
    ease_out = 0.35

    def __init__(self, spec, ctx):
        super().__init__(spec, ctx)
        self.panel = spec.get("panel", "calendar")
        style = (getattr(ctx, "plan", None) or {}).get("style")
        self.scrap = style == "scrapbook"
        self.top = 420 if self.scrap else 230
        self.ph = PANEL_BOTTOM - self.top
        self._bg = None
        self._shadow = None
        self.t0 = self.start + 0.35          # panel content starts once the push is under way

    # ------------------------------------------------------------ layout: background, card, panel
    def _background(self):
        if self._bg is None:
            bg = Image.new("RGB", (W, H), (255, 244, 248))
            d = ImageDraw.Draw(bg)
            for x in range(0, W, 72):                                 # soft pink stripes like a journal page
                d.rectangle((x, 0, x + 36, H), fill=(252, 226, 238))
            r = np.random.default_rng(5)
            from gfx import sparkle
            for _ in range(14):
                sp = sparkle(int(r.uniform(18, 34)), "#FFFFFF", glow_blur=2)
                bg.paste(sp, (int(r.uniform(20, W - 40)), int(r.uniform(150, H - 60))), sp)
            if not self.scrap:
                bg = Image.new("RGB", (W, H), (246, 244, 240))
            self._bg = bg
        return self._bg

    def whole(self, frame, t):
        e = self.env(t)
        if e <= 0.001:
            return frame
        k = out_cubic(e)
        sc = lerp(1.0, CARD_SCALE, k)
        cw, ch = int(W * sc), int(H * sc)
        cy = lerp(H / 2, CARD_TOP + H * CARD_SCALE / 2, k)
        out = self._background().copy()
        if k < 1:
            out = Image.blend(frame.resize((W, H)), out, min(1, k * 1.4)) if k < 0.7 else out
        card = frame.resize((cw, ch), Image.BILINEAR)
        border = int(12 * k)
        if border:
            framed = Image.new("RGB", (cw + 2 * border, ch + 2 * border), (255, 255, 255))
            framed.paste(card, (border, border))
            card = framed
        card = rounded(card, int(40 * k))
        if k > 0.98:
            if self._shadow is None or self._shadow.size != (card.width + 80, card.height + 80):
                sh = Image.new("RGBA", (card.width + 80, card.height + 80), (0, 0, 0, 0))
                sh.paste((60, 20, 50, 90), (40, 52), card.getchannel("A"))
                self._shadow = sh.filter(ImageFilter.GaussianBlur(16))
            out.paste(self._shadow, (int(W / 2 - self._shadow.width / 2), int(cy - self._shadow.height / 2)), self._shadow)
        out.paste(card, (int(W / 2 - card.width / 2), int(cy - card.height / 2)), card)
        panel = self.draw_panel(t - self.t0)
        a = min(1.0, max(0.0, (k - 0.3) / 0.7))
        if panel is not None and a > 0.01:
            panel = xform(panel, alpha=a) if a < 1 else panel
            out.paste(panel, (0, self.top), panel)
            if not self.scrap and self.s.get("title"):
                head = text_img(self.s["title"], UI_BOLD, 54, INK)
                out.paste(head, (int(W / 2 - head.width / 2), self.top - 90), head)
        return out

    # ------------------------------------------------------------ panels
    def draw_panel(self, L):
        if L < 0:
            return None
        return getattr(self, "_" + self.panel.replace("-", "_"))(L)

    def _card(self, w, h, fill=(255, 255, 255)):
        h = min(h, self.ph - 40)                       # its shadow must fit inside the panel too
        c = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        ImageDraw.Draw(c).rounded_rectangle((0, 0, w - 1, h - 1), 34, fill=fill + (255,))
        return drop_shadow(c, 0, 10, 14, (70, 30, 60, 80))

    def _calendar(self, L):
        """Month view; events land on their days one by one, each with a cursor click."""
        today = datetime.date.today()
        year, month = int(self.s.get("year", today.year)), int(self.s.get("month", today.month))
        events = self.s.get("events") or [{"day": 6, "text": "meeting"}, {"day": 9, "text": "dentist"},
                                          {"day": 13, "text": "deadline"}, {"day": 16, "text": "family"}]
        week = cal.Calendar(firstweekday=6).monthdayscalendar(year, month)
        P = Image.new("RGBA", (W, self.ph), (0, 0, 0, 0))
        cw, chh = 1000, self.ph - 40
        card = self._card(cw, chh)
        d = ImageDraw.Draw(card)
        d.text((50, 30), cal.month_name[month], font=font(UI_BOLD, 50), fill=INK)
        d.text((50 + font(UI_BOLD, 50).getlength(cal.month_name[month]) + 16, 44), str(year), font=font(UI, 36),
               fill=(150, 140, 150))
        d.rounded_rectangle((cw - 230, 34, cw - 130, 80), 23, outline=(210, 200, 215), width=3)
        d.text((cw - 212, 40), "today", font=font(UI, 28), fill=(120, 110, 125))
        d.text((cw - 100, 30), "‹  ›", font=font(UI_BOLD, 44), fill=(150, 140, 150))
        gx, gy, colw = 40, 104, (cw - 80) / 7
        rowh = (chh - gy - 34) / max(len(week), 5)
        for i, wd in enumerate("SMTWTFS"):
            d.text((gx + colw * i + colw / 2 - 9, gy - 10), wd, font=font(UI_BOLD, 26), fill=(160, 150, 165))
        cells = {}
        for r, row in enumerate(week):
            for c, day in enumerate(row):
                if not day:
                    continue
                x, y = gx + colw * c, gy + 30 + rowh * r
                cells[day] = (x, y)
                d.line((x + 6, y, x + colw - 6, y), fill=(238, 232, 240), width=2)
                is_today = day == self.s.get("today", today.day if (year, month) == (today.year, today.month) else -1)
                if is_today:
                    d.ellipse((x + colw / 2 - 21, y + 1, x + colw / 2 + 21, y + 43), fill=rgba("#EE5FA7"))
                d.text((x + colw / 2, y + 22), str(day), font=font(UI_BOLD if is_today else UI, 30),
                       fill=(255, 255, 255) if is_today else INK, anchor="mm")
        cur = _cursor()
        last_xy = (cw * 0.8, chh * 0.9)
        for i, ev in enumerate(events):
            at = 0.35 + 0.5 * i
            day = int(ev.get("day", 1))
            if day not in cells:
                continue
            x, y = cells[day]
            p = prog(L, at, 0.25)
            if L >= at - 0.35:                                   # the cursor travels to the day, then clicks
                m = out_cubic(prog(L, at - 0.35, 0.35))
                last_xy = (lerp(last_xy[0], x + colw * 0.72, m), lerp(last_xy[1], y + rowh * 0.7, m))
            if p > 0:                                            # the day lights up and gets its label
                col = ev.get("color") or PASTELS[i % len(PASTELS)]
                cell = Image.new("RGBA", (int(colw - 8), int(rowh - 4)), (0, 0, 0, 0))
                cd = ImageDraw.Draw(cell)
                cd.rounded_rectangle((0, 0, cell.width - 1, cell.height - 1), 14, fill=rgba(col))
                cd.text((cell.width / 2, 20), str(day), font=font(UI_BOLD, 30), fill=INK, anchor="mm")
                label = ev.get("text", "")
                fs = 20
                while fs > 13 and font(UI_BOLD, fs).getlength(label) > cell.width - 8:
                    fs -= 1
                cd.text((cell.width / 2, cell.height - 15), label, font=font(UI_BOLD, fs), fill=INK, anchor="mm")
                cell = xform(cell, scale=lerp(0.4, 1, out_back(p, 2.0)))
                card.alpha_composite(cell, (int(x + colw / 2 - cell.width / 2), int(y + rowh / 2 - cell.height / 2 - 2)))
        P.alpha_composite(card, (int(W / 2 - card.width / 2), 0))
        cx = W / 2 - card.width / 2 + last_xy[0]
        press = any(0 <= L - (0.35 + 0.5 * i) < 0.12 for i in range(len(events)))
        _put(P, xform(cur, scale=0.85 if press else 1.0), cx, last_xy[1] + 10)
        return P

    def _popups(self, L):
        """Retro pop-up windows pile up, one per item, slightly offset like a desktop gone wild."""
        items = self.s.get("items") or ["kerja", "family", "tanggungjawab", "to-do list (47)", "goals 2026"]
        P = Image.new("RGBA", (W, self.ph), (0, 0, 0, 0))
        n = len(items)
        step_x, step_y = min(90, 420 / max(n - 1, 1)), min(62, (self.ph - 250) / max(n - 1, 1))
        x0 = W / 2 - step_x * (n - 1) / 2
        y0 = 130
        for i, item in enumerate(items):
            at = 0.1 + float(self.s.get("every", 0.28)) * i
            p = prog(L, at, 0.22)
            if p <= 0:
                continue
            win = self._window(item, i)
            rot = (-3, 2, -1, 3, -2, 1)[i % 6]
            _put(P, xform(win, scale=lerp(0.3, 1, out_back(p, 2.2)), rot=rot), x0 + step_x * i, y0 + step_y * i)
        return P

    def _window(self, text, i):
        key = ("win", text, i)
        if not hasattr(self, "_cache"):
            self._cache = {}
        if key not in self._cache:
            w, h = 600, 210
            img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
            d = ImageDraw.Draw(img)
            d.rounded_rectangle((0, 0, w - 1, h - 1), 16, fill=(255, 251, 240, 255), outline=(60, 40, 60, 255), width=4)
            d.rounded_rectangle((0, 0, w - 1, 48), 16, fill=rgba(PASTELS[i % len(PASTELS)]), outline=(60, 40, 60, 255),
                                width=4)
            d.rectangle((4, 30, w - 5, 46), fill=rgba(PASTELS[i % len(PASTELS)]))
            d.line((0, 48, w, 48), fill=(60, 40, 60, 255), width=4)
            for j in range(3):
                d.ellipse((w - 110 + j * 32, 14, w - 90 + j * 32, 34), fill=(255, 255, 255, 255), outline=(60, 40, 60, 255), width=3)
            d.text((18, 8), "reminder!!", font=font(UI_BOLD, 26), fill=(60, 40, 60))
            d.ellipse((24, 82, 84, 142), fill=rgba("#EE5FA7"))
            d.text((54, 112), "!", font=font(UI_BOLD, 44), fill=(255, 255, 255), anchor="mm")
            fs = 46
            while fs > 26 and font(CHUNKY, fs).getlength(text) > w - 130:
                fs -= 2
            d.text((104, 112), text, font=font(CHUNKY, fs), fill=rgba(PLUM), anchor="lm")
            d.rounded_rectangle((w - 120, h - 52, w - 24, h - 14), 12, fill=(255, 255, 255, 255), outline=(60, 40, 60, 255), width=3)
            d.text((w - 72, h - 33), "ok", font=font(UI_BOLD, 26), fill=(60, 40, 60), anchor="mm")
            self._cache[key] = drop_shadow(img, 6, 8, 4, (60, 30, 50, 120))
        return self._cache[key]

    def _todo_scroll(self, L):
        """A to-do list that keeps scrolling: the point is that it never ends."""
        base = self.s.get("items") or ["reply emails", "laundry", "meeting prep", "groceries", "edit video",
                                       "call mak", "gym", "pay bills", "content plan", "clean room"]
        total = int(self.s.get("count", 47))
        cw, chh = 860, self.ph - 40
        card = self._card(cw, chh, (255, 252, 244))
        d = ImageDraw.Draw(card)
        head = text_img(self.s.get("title", "to-do list"), SCRIPT, 82, PLUM, stroke=1, stroke_fill=PLUM)
        card.alpha_composite(head, (40, 8))
        shown = min(total, int(4 + 26 * out_cubic(prog(L, 0, 2.2))))
        badge = f"{shown}"
        d.rounded_rectangle((cw - 150, 34, cw - 40, 90), 28, fill=rgba("#EE5FA7"))
        d.text((cw - 95, 62), badge, font=font(UI_BOLD, 36), fill=(255, 255, 255), anchor="mm")
        rowh = 64
        top = 130
        speed = 260 * (prog(L, 0, 2.4) ** 1.6) * 2.4                      # accelerating scroll
        off = speed % rowh
        first = int(speed // rowh)
        for j in range(-1, int((chh - top) / rowh) + 1):
            y = top + j * rowh - off
            if y < top - 10 or y > chh - 40:
                continue
            n = first + j
            d.ellipse((50, y + 12, 86, y + 48), outline=rgba("#C9B6F5"), width=4)
            d.text((110, y + 30), base[n % len(base)], font=font(UI, 38), fill=INK, anchor="lm")
            d.line((110, y + rowh - 2, cw - 50, y + rowh - 2), fill=(236, 230, 236), width=2)
        P = Image.new("RGBA", (W, self.ph), (0, 0, 0, 0))
        P.alpha_composite(card, (int(W / 2 - card.width / 2), 0))
        return P

    def _time_bars(self, L):
        """Free hours per day grow as bars; the total counts up underneath."""
        days = self.s.get("days") or ["isn", "sel", "rab", "kha", "jum", "sab", "ahd"]
        hours = self.s.get("hours") or [1, 0.5, 2, 1, 0.5, 4, 3]
        label = self.s.get("label", "free time minggu ni")
        unit = self.s.get("unit", "jam")
        cw, chh = 900, self.ph - 40
        card = self._card(cw, chh)
        d = ImageDraw.Draw(card)
        head = text_img(label, CHUNKY, 46, PLUM)
        card.alpha_composite(head, (50, 22))
        n = len(days)
        bw = (cw - 120) / n
        base_y = min(chh, self.ph - 40) - 70
        top_y = 140
        hmax = max(max(hours), 1)
        total = 0.0
        for i, (day, hv) in enumerate(zip(days, hours)):
            p = out_back(prog(L, 0.2 + 0.18 * i, 0.4), 1.4)
            total += hv * min(1, max(0, p))
            bh = (base_y - top_y - 40) * hv / hmax * max(0, p)
            x0 = 60 + bw * i + 14
            d.rounded_rectangle((x0, base_y - bh, x0 + bw - 28, base_y), 14, fill=rgba(PASTELS[i % 2]))
            d.text((x0 + (bw - 28) / 2, base_y + 30), day, font=font(UI_BOLD, 26), fill=(130, 115, 130), anchor="mm")
            if p > 0.6:
                d.text((x0 + (bw - 28) / 2, base_y - bh - 22), f"{hv:g}", font=font(UI_BOLD, 26), fill=INK, anchor="mm")
        d.line((50, base_y, cw - 50, base_y), fill=(220, 210, 222), width=3)
        P = Image.new("RGBA", (W, self.ph), (0, 0, 0, 0))
        P.alpha_composite(card, (int(W / 2 - card.width / 2), 0))
        k = prog(L, 0.2 + 0.18 * n, 0.3)
        if k > 0:
            pill = text_img(f"= {total:g} {unit}", CHUNKY, 64, "#FFFFFF", stroke=4, stroke_fill="#EE5FA7",
                            shadow=(0, 4, 8, (80, 20, 60, 120)))
            _put(P, xform(pill, scale=lerp(0.5, 1, out_back(k, 2.0)), rot=-4), W / 2 + 290, 48)
        return P

    def _goals(self, L):
        """Goal cards pop in; then the chosen ones light up with a check and the rest fade back."""
        goals = self.s.get("goals") or ["side hustle", "gym", "baca buku", "belajar bahasa", "content", "savings"]
        picks = set(self.s.get("picks", [0, 1]))
        pick_at = float(self.s.get("pick_at", 1.6))
        P = Image.new("RGBA", (W, self.ph), (0, 0, 0, 0))
        cols, rows = 3, (len(goals) + 2) // 3
        gw, gh = 290, min(170, (self.ph - 30) / rows - 20)
        sel = prog(L, pick_at, 0.35)
        for i, g in enumerate(goals):
            r, c = divmod(i, cols)
            x = W / 2 + (c - 1) * (gw + 22)
            y = 20 + gh / 2 + r * (gh + 24)
            p = prog(L, 0.1 + 0.12 * i, 0.25)
            if p <= 0:
                continue
            chosen = i in picks
            card = Image.new("RGBA", (gw, int(gh)), (0, 0, 0, 0))
            dd = ImageDraw.Draw(card)
            fill = rgba(PASTELS[i % len(PASTELS)])
            if not chosen and sel > 0:
                fill = tuple(int(lerp(v, 225, sel)) for v in fill[:3]) + (255,)
            dd.rounded_rectangle((0, 0, gw - 1, gh - 1), 26, fill=fill,
                                 outline=rgba("#EE5FA7") if chosen and sel > 0 else (255, 255, 255, 255),
                                 width=8 if chosen and sel > 0 else 4)
            txt = text_img(g, CHUNKY, 40, PLUM if (chosen or sel == 0) else "#9C8E9A")
            if txt.width > gw - 30:
                txt = xform(txt, scale=(gw - 30) / txt.width)
            card.alpha_composite(txt, (int(gw / 2 - txt.width / 2), int(gh / 2 - txt.height / 2)))
            sc = lerp(0.4, 1, out_back(p, 2.0)) * (1 + (0.08 * out_back(sel, 2) if chosen else -0.06 * sel))
            _put(P, xform(drop_shadow(card, 0, 6, 8, (70, 30, 60, 70)), scale=sc), x, y)
            if chosen and sel > 0:
                dot = Image.new("RGBA", (74, 74), (0, 0, 0, 0))
                dd2 = ImageDraw.Draw(dot)
                dd2.ellipse((0, 0, 73, 73), fill=rgba("#EE5FA7"), outline=(255, 255, 255, 255), width=4)
                dd2.line([(20, 38), (32, 50), (54, 24)], fill=(255, 255, 255, 255), width=8, joint="curve")
                _put(P, xform(dot, scale=out_back(sel, 2.2)), x + gw / 2 - 20, y - gh / 2 + 10)
        return P

    # ------------------------------------------------------------ sound cues
    def cues(self):
        """(time, sound, gain, priority): the push gets a zoom; the panel's beats get clicks, pops and blobs."""
        t0 = self.t0
        ev = [(self.start, "zoom", 0.16, 2)]
        n = self.panel
        if n == "calendar":
            evs = self.s.get("events") or [0, 0, 0, 0]
            ev += [(t0 + 0.35 + 0.5 * i, "click", 0.2, 2) for i in range(len(evs))]
        elif n == "popups":
            items = self.s.get("items") or [0] * 5
            ev += [(t0 + 0.1 + float(self.s.get("every", 0.28)) * i, "pop", 0.16, 2) for i in range(len(items))]
        elif n == "todo-scroll":
            ev += [(t0 + 0.2 * i, "click", 0.12, 2 if i < 4 else 1) for i in range(8)]
        elif n == "time-bars":
            days = self.s.get("days") or [0] * 7
            ev += [(t0 + 0.2 + 0.18 * i, "blob", 0.1, 1) for i in range(len(days))]
            ev += [(t0 + 0.2 + 0.18 * len(days), "ding", 0.12, 2)]
        elif n == "goals":
            goals = self.s.get("goals") or [0] * 6
            ev += [(t0 + 0.1 + 0.12 * i, "pop", 0.12, 2 if i == 0 else 1) for i in range(len(goals))]
            ev += [(t0 + float(self.s.get("pick_at", 1.6)), "blob", 0.18, 2)]
        return ev
