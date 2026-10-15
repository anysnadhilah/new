# The three styles

All graphics are drawn by code (no stock art, no licensed samples). Fonts are Google Fonts (SIL Open Font License),
downloaded by setup. Each style lives in `scripts/styles/<name>.py`; the knobs are the constants at the top.

## whimsical (`styles/whimsical.py`)
Dreamy, magical, soft.
- Grade: lifted, slightly pink/blue, gentle bloom (screen-blended blur) + soft pink edge haze.
- Captions: Fredoka, white, thick pastel outline (pink, lilac, sky, mint, cycling per caption). Each word
  bounces in on its spoken frame (overshoot + tilt), then floats gently.
- Punch word: Pacifico script in the caption's pastel, white outline; three little hearts float up from it.
- Always on: twinkling sparkles around each caption, bubbles drifting up the side margins.
- Cuts: soft white flash + sparkle burst.
- Hook: bubbly letters drop in one by one, script label above, sparkles around.
- Stickers: `heart`, `star`, `sparkle`.
- Sound: twinkle on cuts, pop on punch words and stickers.
- Assemble push: 0.

## it-girl (`styles/it_girl.py`)
Chic, confident, expensive. Use for "cool girl", "clean girl", "aesthetic", "luxury".
- Grade: warm creamy film (lifted blacks, rolled-off highlights, lower saturation) + vignette.
- Captions: Jost, cream, lowercase, calm. Words fade up out of a soft blur as they are spoken.
- Punch word: Bodoni Moda italic, large, letters rise from an invisible baseline; a hairline draws itself under it.
- Always on: a thin cream frame line fades in at the start. Slow push-in on every shot (assemble `--push 0.035`).
- Cuts: a warm light leak sweeps across.
- Hook: tracked-caps label between two sparkles + big italic serif title.
- Stickers: `sparkle`, `label` (tracked caps, needs `text`).
- Sound: soft whoosh on cuts, tick on punch words.

## scrapbook (`styles/scrapbook.py`)
Crafty, playful, personal.
- Grade: warm, a touch more contrast, mild vignette. Torn kraft + paper edges at the very top and bottom
  (inside the Instagram UI area, so they frame the preview without hiding anything).
- Captions: Special Elite typewriter text on torn paper strips with tape, strips slap down, words type on.
- Punch word: ransom-note cut-out letters (mixed fonts and paper colours), popping in one by one;
  a marker underline, circle or arrow draws itself.
- Cuts: every third cut a kraft paper sheet wipes across; the others get a camera-shutter flash.
- Hook: big ransom-letter title + handwritten label on a taped note.
- Stickers: `star`, `heart`, `smiley`, `note` (handwritten on yellow paper, needs `text`).
- Sound: paper slap on strips, tick per ransom letter, whoosh on wipes, shutter on flashes.

## Adding a fourth style
Copy the closest style file, rename the class and `STYLE = ...`, change fonts/colours/motion, and register it in
`STYLES` in `scripts/render.py` and `scripts/plan.py`. Every style implements the same hooks
(`grade`, `word_img`, `animate`, `behind`, `front`, `draw_hook`, `draw_sticker`, `draw_cut`, `ambient`, `sfx`)
from `styles/base.py`, which already handles timing, layout, face-safe placement and the safe area.
