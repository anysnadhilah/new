"""Sound design. Sound marks moments; it is not decoration. Every candidate sound gets a priority:

  3  intro (the hook)
  2  bullet points (checklist ticks, chapter titles, list pills), key transitions (zoom-through, phone frame,
     pull-back, app split, dolly zoom) and big punches (punch zoom with words, cover / glass titles, chart landing)
  1  other effect entrances
  0  small decoration (per-caption pops, per-card / per-letter ticks, sparkles)

direct() keeps what the level allows and spaces the survivors so they never crowd: "subtle" keeps 3s and the
strongest 2s, "normal" keeps 2s, "bold" adds 1s. Gains stay well under the voice.
"""

LEVELS = {"off": 0.0, "subtle": 0.55, "normal": 0.8, "bold": 1.0}
MIN_PRIORITY = {"subtle": 2, "normal": 2, "bold": 1}
SPACING = {"subtle": 3.0, "normal": 2.0, "bold": 1.2}           # seconds between two sounds
KEY_ENTRANCES = {"zoom-through", "phone-frame", "pull-back", "app-split", "dolly-zoom", "cover-title", "glass-title",
                 "checklist", "chart-grow"}
BULLET_STICKERS = {"chapter", "pill", "pill-yellow", "note"}


def direct(events, plan):
    """events: (time, name, gain, priority). Returns the (time, name, gain) that should actually play."""
    lvl = plan.get("sfx", "normal")
    if lvl not in LEVELS or LEVELS[lvl] == 0:
        return []
    keep, spacing = [], SPACING[lvl]
    for t, name, gain, pri in sorted(events, key=lambda e: (-e[3], e[0])):
        if pri < MIN_PRIORITY[lvl]:
            continue
        # bullet ticks of one list may follow each other closer; everything else keeps the full spacing
        if any(abs(t - k[0]) < (0.8 if name == k[1] == "ding" else spacing) for k in keep):
            continue
        keep.append((t, name, gain * LEVELS[lvl], pri))
    return sorted((t, n, g) for t, n, g, _ in keep)


def effect_sounds(e):
    """Candidate sounds for one effect, as (time, name, gain, priority)."""
    out = []
    first = True
    for t, name, gain in _effect_sounds(e):
        if first:
            pri = 2 if e.name in KEY_ENTRANCES or (e.name == "punch-zoom" and getattr(e, "lines", None)) else 1
            first = False
        else:
            pri = 2 if (e.name == "checklist" and name == "ding") else (2 if name == "impact" else 0)
        out.append((t, name, gain, pri))
    return out


def _effect_sounds(e):
    s, end = e.start, e.end
    n = e.name
    ev = []
    if n == "punch-zoom":
        ev += [(s, "impact", 0.14)] if getattr(e, "lines", None) else [(s, "swish", 0.1)]
    elif n == "zoom-through":
        ev += [(e.at - 0.4, "whoosh", 0.2)]
    elif n == "phone-frame":
        ev += [(s, "swish", 0.16), (end - 0.3, "boop", 0.12)]
    elif n == "pull-back":
        ev += [(s, "swoosh", 0.16)]
        span = max(0.4, end - s - 1.4) / max(len(e.items), 1)
        ev += [(s + e.ease_in + span * (i + 0.5), "ding", 0.07) for i in range(len(e.items))]
    elif n == "app-split":
        ev += [(s, "swish", 0.16)] + [(s + 0.35 + 0.12 * i, "pop", 0.08) for i in range(len(e.thumbs))]
        ev += [(s + 1.0, "typing", 0.12)]
    elif n == "dolly-zoom":
        ev += [(s, "riser", 0.12), (s + 0.6, "swoosh", 0.08)]
    elif n == "checklist":
        ev += [(s, "pop", 0.14)] + [(a, "ding", 0.09) for a in e.at]
    elif n == "phone-float":
        ev += [(s, "swish", 0.14)] + [(s + 0.4 + 1.1 * i, "notify", 0.12) for i in range(len(e.messages))]
    elif n in ("note-wall", "headline-wall"):
        ev += [(s + i * e.every, "pop" if i % 2 == 0 else "tick", 0.07) for i in range(len(e.cards))]
    elif n == "chart-grow":
        ev += [(s + 0.3, "riser", 0.08), (s + 0.3 + (end - s) * 0.55, "ding", 0.1)]
    elif n == "orbit":
        ev += [(s, "whoosh", 0.14)]
    elif n == "new-background":
        ev += [(s, "swish", 0.16)]
    elif n == "paper-cutout":
        ev += [(s, "rustle", 0.2)] + [(s + 0.2 + 0.12 * i, "tick", 0.07) for i in range(len(e.letters))]
    elif n == "doodle-outline":
        ev += [(s, "chime", 0.1), (s + 0.3, "rustle", 0.08)]
    elif n == "cover-title":
        ev += [(s, "impact", 0.18), (s + 0.1, "shutter", 0.08)]
    elif n == "glass-title":
        ev += [(s, "chime", 0.12), (s + 0.15, "impact", 0.12)]
    return ev
