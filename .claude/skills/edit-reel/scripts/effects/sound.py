"""Sound design for the effects: which sounds play when, for each effect. (time, sound name, gain) events,
mixed under the voice by render.py and scaled by plan.json "sfx" (off | subtle | normal | bold)."""

LEVELS = {"off": 0.0, "subtle": 0.6, "normal": 1.0, "bold": 1.45}


def level(plan):
    v = plan.get("sfx", "normal")
    return LEVELS.get(v, v if isinstance(v, (int, float)) else 1.0)


def effect_sounds(e):
    s, end = e.start, e.end
    n = e.name
    ev = []
    if n == "punch-zoom":
        ev += [(s - 0.55, "riser", 0.10), (s, "impact", 0.16)]
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
