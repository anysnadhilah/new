# The three styles

All graphics are drawn by code (no stock art, no licensed samples). Fonts are Google Fonts (SIL Open Font License),
downloaded by setup. Each style lives in `scripts/styles/<name>.py`; the knobs are the constants at the top.
The hook (`plan.json` → `hook`) takes `text`, optional `label` (small kicker) and optional `sub` (small line under).
Hooks shrink automatically to fit the free space around the head.

## it-girl (`styles/it_girl.py`)
Clean, chic, editorial. Use for "it girl", "cool girl", "clean girl", "aesthetic", "luxury".
- Grade: natural and bright, a touch of warmth. No frame, no light leaks, clean cuts: the restraint is the look.
- Captions: Tinos (classic Times-like serif), white, tight tracking, soft shadow. A whole phrase fades in at once.
- Punch word (`emph`): same serif set big on its own line, so the key line dominates ("you / don't have / to be a").
- Hook: italic serif `label` above, big serif line, optional small `sub` line under.
- Stickers:
  - `chapter` + `text`: bold butter-yellow caps title, e.g. "1. plan your week" (great for list videos; give it
    the whole section as `dur`).
  - `italic` + `text`: white italic serif label, e.g. a method or product name.
- Sound: almost none (tick on stickers). Assemble push: 0.025.

## whimsical (`styles/whimsical.py`)
Cosy, dreamy, playful.
- Grade: warm cream with a soft bloom (fairy-light glow).
- Captions: Figtree ExtraBold, lowercase, tight tracking, stacked tight. Line 1 cream, line 2 butter yellow.
  Words pop in on their spoken frame and float gently.
- Punch word: butter yellow, bigger, own line.
- Always on: thin white asterisk sparkles twinkle and turn beside each caption.
- Hook: big stacked two-tone headline, `label` becomes a yellow pill under it, asterisks around.
- Stickers:
  - `pill` + `text` (+ optional `value` shown bold on the right, like "revenue  $21,389"): white rounded chip.
  - `pill-yellow` + `text`: butter-yellow chip.
  - `aside` + `text`: small "(text in brackets)" note.
  - `asterisk` / `star`: a big twinkling sparkle.
- Cuts: a very soft warm flash. Sound: pop on punch words and stickers, twinkle on the hook.

## scrapbook (`styles/scrapbook.py`)
A journal page that talks (studied from engaging creator reels; our own build). The structure carries it: **one
pinned title per idea**, everything else stays quiet.
- Grade: soft, slightly warm and pastel.
- **Section titles** (plan.json `sections`, plus the `hook` as the first one) are pinned at the top for the whole
  section: a handwritten cream kicker (Sacramento, writes itself on) over chunky lavender words (Fredoka Bold, plum
  edge) and an optional pink serif line (Instrument Serif). The words fly together from scattered spots with a
  sparkle burst in about half a second, then stay perfectly still. Two small sparkles and one 3D gem stay beside it.
  Titles may come down over hair or hijab to the brows, never onto the eyes; they shrink (to 62% at most) when the
  face is close to the top.
- Camera (the visual hook): a slow push-in through the hook that lands with a punch on its last word; every new
  section lands with a punch-in and alternates a wider and a closer framing (like a two-camera edit), drifting closer
  while the idea is explained; a caption with an `emph` word jumps a little closer. Zooms are anchored on the eyes so
  the titles stay clear, and pause while an effect is on screen.
- Decor: acrylic craft gems (faceted stars, hearts and round rhinestones in pink, blue, lilac, yellow, red, green,
  clear) burst out of every title as it lands and settle around it, still.
- Hook: the kicker writes on at once; the title words fly in one by one **on the words as they are spoken**; three
  gems pop in around the speaker.
- Captions: small, quiet white sans subtitles low on the frame (about 78% down, below the chin), the whole phrase at
  once. The `emph` word turns butter yellow; no size jumps.
- Stickers:
  - `aside` + `text` ("line one|line two"): a handwritten-feel serif side remark on the shoulder (e.g. "I've read
    almost|100 books so far!"), `side` right|left. The caption under it drops to the lowest line.
  - `gem` + `kind` (`acrylic-star-<colour>`, `acrylic-heart-<colour>`, `acrylic-round-<colour>` with colour pink,
    blue, lilac, yellow, red, green, clear or rose; or chrome-star, gold-star, jelly-star, jelly-flower-pink,
    jelly-flower-peach, jelly-flower-lilac, rhinestone-heart, rhinestone-flower, sequin, holo-heart, disco,
    chrome-sparkle), optional `size` (default 150). May sit over hair/hijab, never the face.
  - `star`, `heart`: shortcuts for chrome-star and rhinestone-heart.
  - `note` + `text`: handwritten words on a torn yellow note.
  - `photo` + `file` (path inside the project, e.g. `photos/book.jpg`), optional `w`: a taped print. Ask the user for
    photos that fit the story (places, products, screenshots) and drop them in `<project>/photos/`.
- Motion graphics are a must in this style (aim for something moving every 4-6 s besides the titles):
  `zoom-through` on the cut where each new idea starts, `doodle-outline` on a feeling, `paper-cutout` on a dramatic
  word ("sos!"), `punch-zoom` with text on the key line, `dolly-zoom` on a realisation, a `checklist` recap of the
  steps (drawn as a yellow notepad with a lilac clip in this style), `cover-title` / `glass-title` for the name of
  the method. Skip phone-float, walls, app-split, phone-frame and pull-back: they fight the pinned title. Effects that
  hide captions or own the top hide the title while they show.
- Sound: a magic-glow shimmer on every new title (the hook first) and nothing on ordinary captions; on "bold" also
  a swish per sticker and a pencil scribble for asides and kickers. A music bed (the user's own `music.mp3` in the
  project) suits this style well.

### Writing sections
Split the script into ideas of 4 s or more (problem, each step / tip / item, the turn, the takeaway, the name of the
method). For each: `kicker` = the small spoken-style lead in ("step #1:", "agenda item #2:", "the problem:", "so i
call it"), `title` = the point in 2-5 words, lowercase, in the speaker's language (spell English words in English),
`sub` only when a second short line adds something ("lapang? buat lebih"). A section starts on the first word of its
idea and ends where the next begins; sections never overlap. 6-10 sections in a 60 s reel.

## Preview the gems
`PY SK/scripts/gems.py out.jpg` renders every gem on one sheet.

## Adding a fourth style
Copy the closest style file, rename the class and `STYLE = ...`, change fonts/colours/motion, and register it in
`STYLES` in `scripts/render.py` and `scripts/plan.py`. Every style implements the same hooks
(`grade`, `word_img`, `animate`, `behind`, `front`, `draw_hook`, `draw_sticker`, `draw_cut`, `ambient`, `sfx`)
from `styles/base.py`, which already handles timing, layout, face-safe placement and the safe area.
