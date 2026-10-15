# Editing judgement

## Picking takes (edl.json)
- Rebuild the intended script first: list each idea once, in order. People repeat a line until it lands.
- Use the LAST complete, fluent take of each line unless the user says otherwise. Skip false starts, trailing
  "so...", "okay", "bye", coughs, and lines that only set up a retake.
- In point: ~0.05 s before the first word's start. Out point: right after the last word ends (before the breath).
  Whisper often stretches a line's first word backwards into the silence before it; if a cut feels early, trust
  the next word's start minus ~0.3 s instead.
- A sentence may be built from two takes when each half is cleaner, but only when the cut lands in a natural pause.
- Keep the story tight: hook → problem → what they do → payoff/name of the method. 30-60 s is the sweet spot.
- Same angle twice in a row → alternate `zoom` 1.0 / 1.2 to hide the jump cut. assemble.py frames the face and
  lowers the zoom if the head would fill the frame (`"zoom_lock": true` overrides).

## Captions (plan.json)
- Each caption group is 1-4 words shown while they are spoken; the words appear one by one on their timestamps.
- Fix every mishearing by editing `"w"` (keep `"s"`/`"e"`). Common: names, brands, English words inside other
  languages (e.g. "klender" → "kalendar", "gos" → "goals", "-ta" → "ke"). Write the speaker's language the way they
  would type it. Remove a word entirely only if it was never said.
- Merge or split groups by moving words between them (adjust `start`/`end` to the first/last word). A group should
  read in one glance; ~24 characters max.
- `emph`: one word per group, the one that carries the meaning (a feeling, a number, the method name). Not on
  every group: every 2nd-3rd is right. The word must match a word in that group.
- `"zone"`: `auto` puts captions where the frame has the most room (above or below the head). Force `"top"` or
  `"bottom"` if the auto choice jumps around.

## Hook
`{"text": "...", "label": "...", "start": 0, "end": 2.5}` — on screen during the opening line; it replaces the
captions while it shows. 2-5 words, a question or bold claim from the video itself (e.g. "terlalu ambisius?").
The label is a tiny kicker ("real talk", "pov", "my method"). Set `"hook": null` to skip.

## Stickers
`{"type": "heart", "at": 12.4, "dur": 1.6}` plus optional `"x"`, `"y"` (pixels) and `"text"`.
Place 2-5 per reel on moments that deserve a beat: the problem ("overwhelmed" → heart), a tip, the method name
(`note`/`label` with its name). Without x/y they go to the free side of the face near the top.

## Reading notes from the user
- "the captions are too fast/slow" → regroup words (more or fewer per group).
- "too much going on" → fewer emph words and stickers; for whimsical/scrapbook that is the main lever.
- "start later / cut that part" → EDL change, then assemble, then `plan.py --force` (word times changed, so the
  plan must be redrafted) and re-apply your caption fixes, emph, hook and stickers.
