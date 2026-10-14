#!/usr/bin/env python3
"""ffmpeg composite for machines where a full HyperFrames render is too slow / runs out of memory.

graded aroll -> back graphics layer (words behind the head) -> graded cutout -> front graphics layer (captions,
cards, vignette) + the voice and the SFX from index.html (data-start / data-duration / data-volume).
Run from the project folder after:  LAYER=front build.py + render png-sequence -> renders/front
                                    LAYER=back  build.py + render png-sequence -> renders/back
                                    build.py (plain index.html, read here for the SFX)
Usage: python3 work/composite.py renders/reel1-v1.mp4
"""
import math
import os
import re
import subprocess
import sys

out = sys.argv[1]


def mul(a, b):
    return [[sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)] for i in range(3)]


# CSS filter chain: sepia(.18) saturate(.9) contrast(.93) brightness(1.05) hue-rotate(-5deg)
I = [[1, 0, 0], [0, 1, 0], [0, 0, 1]]
S = [[.393, .769, .189], [.349, .686, .168], [.272, .534, .131]]
sep = [[.82 * I[i][j] + .18 * S[i][j] for j in range(3)] for i in range(3)]
s = .9
sat = [[.213 + .787 * s, .715 - .715 * s, .072 - .072 * s], [.213 - .213 * s, .715 + .285 * s, .072 - .072 * s],
       [.213 - .213 * s, .715 - .715 * s, .072 + .928 * s]]
a = math.radians(-5); c, n = math.cos(a), math.sin(a)
hue = [[.213 + c * .787 - n * .213, .715 - c * .715 - n * .715, .072 - c * .072 + n * .928],
       [.213 - c * .213 + n * .143, .715 + c * .285 + n * .140, .072 - c * .072 - n * .283],
       [.213 - c * .213 - n * .787, .715 - c * .715 + n * .715, .072 + c * .928 + n * .072]]
M = mul(hue, mul(sat, sep))
warm = [1.025, 1.0, .965]   # stands in for the soft-light warm overlay (#gwarm), which a transparent layer cannot carry
M = [[M[i][j] * warm[i] for j in range(3)] for i in range(3)]
mix = ':'.join(f'{k}{t}={M[i][j]:.4f}' for i, k in enumerate('rgb') for j, t in enumerate('rgb'))
k, off = 1.05 * .93, 1.05 * .5 * (1 - .93) * 255   # contrast then brightness: v*k + off
lut = ':'.join(f"{ch}='clip(val*{k:.4f}+{off:.2f},0,255)'" for ch in 'rgb')
GRADE = f'colorchannelmixer={mix},lutrgb={lut}'

html = open('index.html', encoding='utf-8').read()
sfx = [(m.group(1), float(m.group(2)), float(m.group(3)), float(m.group(4))) for m in re.finditer(
    r'<audio id="sfx\d+" src="([^"]+)" data-start="([\d.]+)" data-duration="([\d.]+)" data-track-index="\d+" data-volume="([\d.]+)"', html)]

cmd = ['ffmpeg', '-hide_banner', '-loglevel', 'error', '-stats', '-y', '-i', 'assets/aroll.mp4',
       '-c:v', 'libvpx-vp9', '-i', 'assets/subject.webm',
       '-c:v', 'libvpx-vp9', '-i', 'renders/back.webm',
       '-c:v', 'libvpx-vp9', '-i', 'renders/front.webm']
for f, *_ in sfx:
    cmd += ['-i', f]
fc = [f'[0:v]format=rgb24,{GRADE},format=rgba[base]',
      f'[1:v]format=rgba,{GRADE}[subj]',
      '[base][2:v]overlay=format=auto[a]', '[a][subj]overlay=format=auto[b]',
      '[b][3:v]overlay=format=auto,format=yuv420p[v]']
labels = ['[0:a]']
for i, (f, t, d, vol) in enumerate(sfx):
    ms = int(round(t * 1000))
    fc.append(f'[{4 + i}:a]atrim=0:{d:.3f},volume={vol:.3f},adelay={ms}|{ms},aformat=channel_layouts=stereo[s{i}]')
    labels.append(f'[s{i}]')
fc.append(f"{''.join(labels)}amix=inputs={len(labels)}:normalize=0:duration=first[aout]")
cmd += ['-filter_complex', ';'.join(fc), '-map', '[v]', '-map', '[aout]', '-r', '30',
        '-c:v', 'libx264', '-preset', 'medium', '-crf', '17', '-pix_fmt', 'yuv420p', '-g', '30',
        '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', '-shortest', out]
if os.environ.get('TEST_T'):
    cmd[-1:-1] = ['-t', os.environ['TEST_T']]
print(f'{len(sfx)} sfx')
subprocess.run(cmd, check=True)
