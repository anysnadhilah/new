#!/usr/bin/env python3
"""Word timings for the assembled cut -> <project>/words.json (medium.en; these drive every caption).

Usage:  PY transcribe_cut.py <project_dir> ["prompt with names: Claude, Claude Code, skill"] [--lang ms]
--lang: any language but English (e.g. ms for Malay/English mix) uses the multilingual large-v3-turbo model.
Whisper mishears proper nouns ("Claude" -> "cloud"/"claws", "skill" -> "scale", "design" -> "this line"):
pass them in the prompt and still fix captions by hand from what the speaker actually said.
"""
import json
import os
import subprocess
import sys

from faster_whisper import WhisperModel

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import skillenv  # noqa: E402

skillenv.utf8_stdio()
argv = sys.argv[1:]
lang = 'en'
if '--lang' in argv:
    i = argv.index('--lang'); lang = argv[i + 1]; argv = argv[:i] + argv[i + 2:]
proj = skillenv.path_arg(argv[0])
wav = os.path.join(proj, 'work', 'aroll.wav')
os.makedirs(os.path.join(proj, 'work'), exist_ok=True)
prompt = argv[1] if len(argv) > 1 else 'Claude, Claude Code, skill.'
subprocess.run([skillenv.tool('ffmpeg'), '-loglevel', 'error', '-y', '-i', os.path.join(proj, 'assets', 'aroll.mp4'), '-vn', '-ac', '1',
                '-ar', '16000', wav], check=True)
m = WhisperModel('medium.en' if lang == 'en' else 'large-v3-turbo', compute_type='int8')
s, _ = m.transcribe(wav, word_timestamps=True, vad_filter=False, initial_prompt=prompt, language=lang)
ws = [{'text': w.word.strip(), 'start': round(w.start, 3), 'end': round(w.end, 3)} for x in s for w in x.words]
with open(os.path.join(proj, 'words.json'), 'w', encoding='utf-8') as fh:
    json.dump(ws, fh, indent=1)
print(' '.join(f"{w['text']}@{w['start']:.2f}" for w in ws))
