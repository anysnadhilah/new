# The three styles

All graphics are drawn by code (no stock art, no licensed samples). Fonts are Google Fonts (SIL Open Font License),
downloaded by setup. Each style lives in `scripts/styles/<name>.py`; the knobs are the constants at the top.
The hook (`plan.json` → `hook`) takes `text`, optional `label` (small kicker) and optional `sub` (small line under).
Hooks shrink automatically to fit the free space around the head.

## it-girl (`styles/it_girl.py`)
Clean, chic, editorial, a little luxe. Use for "it girl", "cool girl", "clean girl", "aesthetic", "luxury".
- Grade: natural and bright, a touch of warmth. No frame, no light leaks, clean cuts: the restraint is the look.
- Type: Playfair Display. Captions in the regular cut, white, soft shadow, the whole phrase fading in at once.
- Punch word (`emph`): big very light pink italic (Playfair Display Italic, #FBD3E0) on its own line.
- Section titles (2.6 s): a small white italic kicker over the point in light pink italic, with two minimal
  line stars beside it (plan.json `"star"`: burst | outline | spark | cross | asterisk | heart, or two joined by "+" for big + small stars; default burst+spark). Over graphics (split-panel): an ink serif headline on cream editorial paper.
- Signature motion graphic: `circle-title` (see effects.md) on the method name / the turn / the takeaway: light pink
  italic inside a thin oval that draws itself, minimal line stars. Use 1-2 per reel.
- Hook: italic serif `label` above, big serif line, optional small `sub` line under.
- Stickers:
  - `chapter` + `text`: light pink italic serif title, e.g. "1. plan your week".
  - `italic` + `text`: white italic serif label, e.g. a method or product name.
- Sound: whoosh on the hook, zoom on punch-ins, click on chapter titles, pop on stickers, pencil + twinkle on the oval.

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

## Shared by every style
- `sections` (one per idea, see "Writing sections" under scrapbook) drive the **zoom rhythm** in every style: a
  slow push-in through the hook that punches on its last word, a punch-in on every new idea alternating a wider and
  a closer framing, a small jump zoom on lines with an `emph` word (anchored on the eyes). Write sections for every
  reel, whatever the style.
- Each style shows a section's title its own way: scrapbook pins it for the whole idea; it girl shows a chapter
  title (italic serif kicker over butter caps) for 2.6 s; whimsical pops a pill kicker and chunky two-tone words
  with asterisks for 2.6 s. Titles sit above the head (down to the brows at most) and captions stay low meanwhile.
- `split-panel` graphics work in every style, each with its own page behind the cut-out speaker (scrapbook pink
  stripes, it girl cream editorial paper, whimsical warm butter with asterisks) and the idea's title on top.
- Sounds in every style include zoom on punch-ins plus pop / blob / click on titles, graphics and stickers.

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
- Graphics never hide behind the head in this style: when a graphic needs space, use `split-panel` (the speaker is cut out
  of her background and kept big, and the graphic plays above her head). Every reel opens with a motion graphic as its hook (a
  `popups` panel during the hook) and gets 3-5 panels that show what is said (calendar, to-do scroll, time bars,
  goal cards).
- Motion graphics are a must in this style (aim for something moving every 4-6 s besides the titles):
  `zoom-through` on the cut where each new idea starts, `doodle-outline` on a feeling, `paper-cutout` on a dramatic
  word ("sos!"), `punch-zoom` with text on the key line, `dolly-zoom` on a realisation, a `checklist` recap of the
  steps (drawn as a yellow notepad with a lilac clip in this style), `cover-title` / `glass-title` for the name of
  the method in a `split-panel` or as a section title. Skip cover-title, glass-title, orbit, chart-grow, walls,
  phone-float, app-split, phone-frame and pull-back: they hide behind the head or fight the pinned title. Effects that
  hide captions or own the top hide the title while they show.
- Sound (always includes pop, blob, click and zoom, on moments only): a zoom on every punch-in, the magic-glow
  shimmer on every new title, a blob as its gems land, pops for stickers and pop-up windows, clicks for calendar
  and list taps; on "bold" also jump-zoom sounds on key lines and a pencil for asides and kickers. A music bed (the user's own `music.mp3` in the
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
