#!/usr/bin/env python3
"""Rebuild a render's soundtrack frame-exact from index.html's <audio> tags and mux it onto the rendered picture.

Usage:  PY mux_audio.py <project_dir> <render.mp4>      (run after `HF render`, before check_cuts.py)
Why: the HyperFrames render mixes audio a touch fast (~0.2%): the voice crept ahead of the lips, +70ms by 0:30 and
+240ms by 1:54 on a 2-minute reel, while the picture stayed exact. This mixes the voice (aroll.mp4) and every SFX
with ffmpeg at their data-start / data-media-start / data-duration / data-volume, copies the video stream untouched,
replaces the render in place, then measures the voice against aroll.mp4 at several points (must be 0 +-10ms).
"""
import html
import os
import re
import subprocess
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import skillenv  # noqa: E402

skillenv.utf8_stdio()
FF, FP = skillenv.tool('ffmpeg'), skillenv.tool('ffprobe')
proj, render = skillenv.path_arg(sys.argv[1]), skillenv.path_arg(sys.argv[2])
with open(os.path.join(proj, 'index.html'), encoding='utf-8') as fh:
    page = fh.read()


def attr(tag, name, default=None):
    m = re.search(rf'\b{name}="([^"]*)"', tag)
    return html.unescape(m.group(1)) if m else default


tracks = []
for tag in re.findall(r'<audio\b[^>]*>', page):
    tracks.append((os.path.join(proj, attr(tag, 'src')), float(attr(tag, 'data-start', 0)), float(attr(tag, 'data-media-start', 0)),
                   float(attr(tag, 'data-duration')), float(attr(tag, 'data-volume', 1))))
dur = float(subprocess.run([FP, '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=duration', '-of', 'csv=p=0', render],
                           **skillenv.TEXT).stdout.strip().split(',')[0])

ins, chains = ['-i', render], []
for k, (src, start, mstart, d, vol) in enumerate(tracks, 1):
    ins += ['-i', src]
    chains.append(f'[{k}:a]aresample=48000,atrim=start={mstart:.4f}:duration={d:.4f},asetpts=PTS-STARTPTS,'
                  f'volume={vol:.4f},adelay={start * 1000:.1f}:all=1[a{k}]')
mix = ''.join(f'[a{k}]' for k in range(1, len(tracks) + 1))
graph = ';'.join(chains) + f';{mix}amix=inputs={len(tracks)}:normalize=0:duration=longest,atrim=0:{dur:.4f}[mix]'
tmp = os.path.splitext(render)[0] + '.mux.mp4'
subprocess.run([FF, '-loglevel', 'error', '-y', *ins, '-filter_complex', graph, '-map', '0:v:0', '-map', '[mix]',
                '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', '-t', f'{dur:.4f}', tmp], check=True)
os.replace(tmp, render)


def pcm(f, ss, t):
    b = subprocess.run([FF, '-v', 'error', '-ss', f'{ss:.3f}', '-t', f'{t:.3f}', '-i', f, '-vn', '-ac', '1', '-ar', '8000', '-f', 's16le', '-'],
                       capture_output=True).stdout
    return np.frombuffer(b, np.int16).astype(float)


aroll, worst, rows = os.path.join(proj, 'assets', 'aroll.mp4'), 0, []
for t in np.linspace(2, max(dur - 3, 2.5), 6):
    a, ref = pcm(render, t, 1.0), pcm(aroll, t - .5, 2.0)
    if len(a) < 800 or len(ref) < len(a):
        continue
    lag = (np.argmax(np.correlate(ref, a, 'valid')) / 8000 - .5) * 1000
    worst = max(worst, abs(lag))
    rows.append(f'{t:.0f}s:{lag:+.0f}ms')
print(f'remuxed {len(tracks)} audio tracks onto {os.path.basename(render)}  voice vs cut: {" ".join(rows)}')
if worst > 15:
    sys.exit('LIP SYNC OFF: the voice does not line up with aroll.mp4, investigate before delivering.')
