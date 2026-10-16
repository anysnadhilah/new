---
name: edit-reel
description: "Edits raw vertical talking-head clips into a finished Instagram reel in one of three signature styles: it girl (clean editorial serif captions, chapter titles), whimsical (warm glow, chunky two-tone words, twinkling asterisks, pill labels) or scrapbook (collage mixed-font headlines with shiny 3D gem stickers, notes and taped photos). Takes clips from a folder or a Google Drive link, picks the best take of every line, cuts dead air, frames the face, writes word-timed animated captions that never cover the face, adds motion graphics and subtle sound effects, adds any of 17 video effects (punch zoom, zoom-through cut, checklist, floating phone, pull-back reveal, text behind your head, glass titles, dolly zoom, new background, paper cutout, doodle outline, orbit, chart grow, note and headline walls...), then QA-checks every cut. Trigger with /edit-reel or phrases like 'edit my reel', 'edit these clips', 'make a reel from this drive link', 'use the scrapbook style'."
---

# /edit-reel

Raw clips in, finished reel out. The user never opens an editor: they get a draft in the chat, give notes in
plain words, and each round is a quick re-render.

`SK` = this skill's folder (the one holding this SKILL.md), as a full path.
`PY` = `SK/.venv/bin/python` (the skill's own Python, created by setup). Run every script with `PY`.

Before building, read `references/styles.md` (what each style looks like and its knobs),
`references/editing.md` (how to pick takes, fix captions, write hooks, place stickers) and
`references/effects.md` (the 17 motion-graphic / video effects and when to use them).

## Step 0: Setup (every run, a few seconds after the first time)

1. Run `python3 "SK/scripts/setup.py"`. It prints `STATUS` lines and ends with `READY`.
   - A line says `MISSING` → give the user the fix printed on that line, in plain words, and stop until it is READY.
     Mac users without ffmpeg: `brew install ffmpeg` (no Homebrew? https://brew.sh first).
   - Windows is not supported in this version; say so kindly.
2. Look for `SK/config.json`. If missing, ask in ONE message, then save it:
   - Their name and Instagram handle (optional)
   - Default style: **whimsical**, **it girl** or **scrapbook** (offer it girl if unsure)
   - Language they speak in their videos (e.g. English, Malay, mixed) → `language` (`en`, `ms`, or omit for auto)
   - Where projects live (default `~/reels`)
   ```json
   {"name": "...", "instagram": "handle", "defaultStyle": "it-girl", "language": null,
    "projectsDir": "~/reels", "whisperModel": "small"}
   ```

## Step 1: Intake

- Make a project folder `<projectsDir>/<short-slug>` (slug from the topic, e.g. `come-back-method`).
- Clips: a local file/folder, or a Google Drive link (the user must share it as "Anyone with the link"):
  ```
  PY SK/scripts/fetch.py <project> <file | folder | drive link> [--newest 5]
  ```
- Style: whatever the user asked for (cool girl / clean girl / aesthetic → `it-girl`; cute / dreamy / magical →
  `whimsical`; crafty / journal / collage → `scrapbook`), else `defaultStyle`.
- Tell the user right away what you are doing and roughly when the first draft lands (Step 8 has timings).
- Reference links ("make it look like this reel"): `PY SK/scripts/refs.py <project> <links...>` downloads them and
  writes `refs/ref<N>-sheet.jpg`. Look at the sheets, say in plain words what you see (colour, fonts, text placement,
  graphics, pacing), map it onto the closest style and its knobs, and only then build. Take the feel, never copy
  someone's exact design, logo or text. A failed Instagram link → ask for a Drive copy.

## Step 2: Ingest

```
PY SK/scripts/ingest.py <project> [--language ms] [--prompt "names, brands, keywords"]
```
Read `transcript.txt` (every line with times and pauses) and look at `work/sheet.jpg` (framing of each clip).
Word-level times are in `transcript.json`.

## Step 3: Pick the takes → `<project>/edl.json`

Follow `references/editing.md`. In short: rebuild the script line by line, use the LAST complete clean take of
each line, drop false starts, filler, "okay let me redo that", and dead air. Aim for 30-60 s unless the content
needs more. Alternate framing: if two segments in a row come from the same clip/angle, give one `"zoom": 1.2`
(the face is framed automatically; assemble caps the zoom so text always has room).
```json
[{"id": "hook", "clip": "c1", "in": 0.00, "out": 3.30, "zoom": 1.0},
 {"id": "point1", "clip": "c1", "in": 7.35, "out": 12.85, "zoom": 1.2}]
```
Post the EDL to the user as a short table (line, clip, time) and keep going; do not wait for approval.

## Step 4: Assemble

```
PY SK/scripts/assemble.py <project> --push <style push>     # it-girl 0.025, others 0
```
Makes `work/aroll.mkv` (1080x1920, 30 fps) and `timeline.json` (segments, words in reel time, face boxes).
About 3-4 s per second of reel on a laptop CPU for 4K HEVC phone footage; faster for 1080p.

## Step 5: Plan

```
PY SK/scripts/plan.py <project> --style <style>
```
This drafts `plan.json`. Now edit it like an editor (details in `references/editing.md`):
- Fix every misheard word so captions say exactly what was said, in the speaker's language and spelling.
  Never invent words. No em dashes.
- Set `emph` (the punch word) on roughly every 2nd-3rd caption, on the word that carries the meaning.
- Write a `hook` for the first 2-3 s: a short scroll-stopping line (often the opening question) + optional
  `label` and `sub`.
- Add stickers at meaningful moments (types per style in `references/styles.md`): it girl → a `chapter` per
  section of a list video; whimsical → `pill`s for numbers, steps and names; scrapbook → 2-4 `gem`s, `note`s and
  `photo`s on top of the automatic gem dazzle.

## Step 5b: Effects

Pick 2-6 effects from `references/effects.md` that serve the story (or the ones the user asks for by name) and add
them to `plan.json` → `effects`, timed to the words they illustrate. Never two at once. If any is marked cutout:
```
PY SK/scripts/cutout.py <project>          # run in the background; prints progress; only effect frames
```
Re-run it whenever effect times change (it skips work that is already done).

## Step 6: Look before rendering

```
PY SK/scripts/render.py <project> --at 0.5,2.0,<10-14 moments across the reel> --safe
```
Read `work/snap.jpg`. Include the middle of every effect. Check: no text or graphic on the face, everything
inside the red safe lines, punch words read, nothing crowded, cutout edges clean. Fix `plan.json` (shorter captions, other emph, `"zone": "top"` or `"bottom"`) or the EDL, repeat.

## Step 7: Render and QA

```
PY SK/scripts/render.py <project>                 # full quality + 720p phone copy in renders/
PY SK/scripts/check.py <project> renders/<project>-vN.mp4
```
Look at `work/check.jpg`: every after-cut frame shows the new shot cleanly. The audio line must say OK.
Never deliver a render you have not checked.

## Step 8: Deliver

Send the phone copy (`-phone.mp4`) in the chat so the user can watch it on their phone, plus the full-quality file.
In a cloud session, remind them to download both before the session ends.
Say in plain words what you made (style, length, hook) and anything that needs their call. Then iterate on their
notes: caption/sticker/hook notes only need Step 6-7 (re-render); take changes need Steps 3-5 again
(`plan.py --force`, then redo your caption fixes).

Rough timings for a 60 s reel from 3-4 min of 4K phone footage: setup first time ~2 min; ingest ~1.5 min;
assemble ~4 min; render ~2-4 min. First draft in ~15 min on a recent Mac, ~20-25 min in a cloud session.

## Step 9: Review page (after every draft)

Give the user a review page instead of asking for notes in chat:
```
PY SK/scripts/review.py <project>          # writes <project>/review/: index.html, thumbs/, preview.mp4, files.json
```
Publish it with the Artifact tool: `file_path` = `<project>/review/index.html`, `root` = `<project>/review`, `files` =
the map in `review/files.json` (keys and values are the same relative paths), `capabilities` = `{"db": {}}`,
`icon` = "film" on the first publish. Save the returned url into `review/review.json` as `"url"`; every later draft
republishes to that same url (same `file_path` in this session, or pass `url`). Send the user the link and say:
press Keep / Change / Drop on any take or graphic, retype misheard captions, switch the look, pin notes to moments,
then "Mark ready" and tell you "apply my review".

When they do:
1. Export the page's database: ArtifactData `list` with `out_dir` = `<project>/work/review_export` for each of
   `decisions`, `notes` and `meta`.
2. `PY SK/scripts/review_apply.py <project> <project>/work/review_export`: applies drops, caption fixes and the look
   switch, and prints the Changes and notes that need judgement (also in `work/review_todo.json`).
3. Do each printed item in `edl.json` / `plan.json` (a take's "start later" = move its `in`; "use the other take" =
   pick it from `transcript.txt`; an effect "bigger/shorter" = its options and times). Then assemble (only if cuts
   changed), cutout (if cutout effects changed), render, check, `review.py`, and republish to the same url.
4. Tidy the page's database with one ArtifactData `batch`: delete every `decisions` document and `meta/status`
   (pin each with the `version` the list showed), and `update` each note you handled with
   `{"done": true, "reply": "<one short line on what you changed>"}`.
5. Tell the user the page is updated with the new draft.
The page only shows decisions for the current draft version, so stale ones never leak into the next round.

## Hard rules
1. Never put text or graphics on the face (eyes to chin). The scripts place text in free zones; verify on snaps.
2. Everything important inside the Reels safe area: top 250, bottom 1440, sides 60, right 150 below y 1100.
3. Captions say exactly what was said. Fix mishearings; never paraphrase inside captions.
4. Sound effects stay subtle, always under the voice.
5. Never modify or delete the user's original clips. Everything is written inside the project folder.
6. Prove quality from the final render (check.py), not from assumptions.
