"""The effects library: 20 motion-graphic / video effects that can be placed anywhere in a reel via
plan.json "effects". See references/effects.md for what each one does and its options."""
from effects.base import Effect, Matte, frame_index
from effects.cutout_fx import CoverTitle, DoodleOutline, GlassTitle, NewBackground, PaperCutout
from effects.frame_fx import AppSplit, DollyZoom, PhoneFrame, PullBack, PunchZoom, ZoomThrough
from effects.overlay_fx import ChartGrow, Checklist, HeadlineWall, NoteWall, Orbit, PhoneFloat
from effects.split_fx import SplitPanel
from effects.title_fx import CircleTitle, PeekTitle

EFFECTS = {cls.name: cls for cls in (
    PunchZoom, ZoomThrough, PhoneFrame, PullBack, AppSplit, DollyZoom,
    Checklist, PhoneFloat, NoteWall, HeadlineWall, ChartGrow, Orbit,
    NewBackground, PaperCutout, DoodleOutline, CoverTitle, GlassTitle, SplitPanel, CircleTitle, PeekTitle,
)}


def load_effects(plan, timeline=None, project=None, ctx=None):
    if ctx is None:
        from styles.base import Context
        ctx = Context(timeline, plan, project)
    out = []
    for spec in plan.get("effects", []):
        cls = EFFECTS.get(spec.get("type"))
        if cls is None:
            raise SystemExit(f"unknown effect '{spec.get('type')}'. Available: {', '.join(sorted(EFFECTS))}")
        out.append(cls(spec, ctx))
    return out


def any_hides_captions(effects, t):
    return any(e.hides_captions and e.active(t) for e in effects)


def split_at(effects, t):
    """The split-panel effect on screen at t (the style sets its title small at the top), or None."""
    return next((e for e in effects if getattr(e, "keeps_title", False) and e.active(t)), None)


def reserved_zone(effects, t):
    for e in effects:
        if e.reserves and e.active(t):
            return e.reserves
    return None


def compose(frame, t, effects, matte):
    """Apply the active effects to one graded RGB frame. Returns the new RGB frame."""
    active = [e for e in effects if e.active(t)]
    if not active:
        return frame
    m = matte.at(frame_index(t)) if any(e.needs_matte for e in active) else None
    for e in active:
        e.ctx_matte = m
    if m is not None:
        bg = frame
        for e in active:
            bg = e.background(bg, t)
        bg = bg.copy() if bg is frame else bg
        for e in active:
            e.behind(bg, t)
        person = frame.convert("RGBA")
        person.putalpha(m)
        for e in active:
            person = e.person(person, m, t)
        bg.paste(person, (0, 0), person)
        frame = bg
    else:
        frame = frame.copy()
    for e in active:
        frame = e.whole(frame, t)
    for e in active:
        e.front(frame, t)
    return frame


__all__ = ["EFFECTS", "Effect", "Matte", "load_effects", "compose", "any_hides_captions", "reserved_zone", "split_at"]
