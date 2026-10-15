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
A collage journal page come to life.
- Grade: warm, a little extra contrast and saturation, light vignette.
- Captions mix type like a magazine collage: plain words alternate per caption between pink serif
  (Playfair Display) and yellow italic serif with a brown outline (Fraunces). The punch word is chunky rounded white
  (Nunito Black) with a hot-pink outline and glow.
- Dazzle: shiny 3D gems pop in around every caption and glint (chrome/gold stars, jelly flowers, rhinestone heart and
  flower, iridescent sequins, holographic heart, disco ball, chrome sparkle); small gems and sequins sit in the
  margins the whole time. Gems never sit on the face.
- Hook: yellow italic `label`, chunky pink-glow headline, pink serif `sub`, with a shower of gems around it.
- Stickers:
  - `gem` + `kind` (one of: chrome-star, gold-star, jelly-star, jelly-flower-pink, jelly-flower-peach,
    jelly-flower-lilac, rhinestone-heart, rhinestone-flower, sequin, holo-heart, disco, chrome-sparkle), optional
    `size` (default 150).
  - `star`, `heart`: shortcuts for chrome-star and rhinestone-heart.
  - `note` + `text`: handwritten words on a torn yellow note.
  - `photo` + `file` (path inside the project, e.g. `photos/book.jpg`), optional `w`: a taped print. Ask the user for
    photos that fit the story (places, products, screenshots) and drop them in `<project>/photos/`.
- Cuts: camera-shutter flash. Sound: shutter on cuts, soft twinkle per caption, pop on punch words and stickers.

## Preview the gems
`PY SK/scripts/gems.py out.jpg` renders every gem on one sheet.

## Adding a fourth style
Copy the closest style file, rename the class and `STYLE = ...`, change fonts/colours/motion, and register it in
`STYLES` in `scripts/render.py` and `scripts/plan.py`. Every style implements the same hooks
(`grade`, `word_img`, `animate`, `behind`, `front`, `draw_hook`, `draw_sticker`, `draw_cut`, `ambient`, `sfx`)
from `styles/base.py`, which already handles timing, layout, face-safe placement and the safe area.
