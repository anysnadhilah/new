"""Cut the chosen takes from the original clips into one clean 1080x1920 30fps a-roll.

    assemble.py <project> [--push 0.0]

Reads edl.json:
  [{"id": "hook", "clip": "c1", "in": 12.66, "out": 15.72, "zoom": 1.0, "cx": 0.5, "cy": 0.45, "push": 0.0}]
  zoom 1.0 = full frame, 1.4 = punch in; cx/cy = centre of the crop (0-1 of the source frame), left out =
  frame the face automatically (face centred, eyes-to-chin around 40% from the top);
  push = slow push-in across the segment (0.04 = 4%); the --push value is the default.

Writes work/aroll.mkv and timeline.json (segments with exact frames, words in reel time, face boxes).
"""
import argparse
import statistics
import subprocess
import sys

from common import FPS, H, SR, W, die, ffprobe, load_json, project_dir, save_json


def crop_box(info, zoom, cx, cy):
    """Crop rectangle (x, y, w, h) in source pixels for a 9:16 window at this zoom and centre."""
    sw, sh = info["width"], info["height"]
    bw = min(sw, sh * 9 / 16)
    bh = bw * 16 / 9
    cw, ch = bw / zoom, bh / zoom
    x = min(max(cx * sw - cw / 2, 0), sw - cw)
    y = min(max(cy * sh - ch / 2, 0), sh - ch)
    return int(x) // 2 * 2, int(y) // 2 * 2, int(cw) // 2 * 2, int(ch) // 2 * 2


def auto_frame(seg, info, samples):
    """Fill in cx/cy: centre the face horizontally and put it at ~40% height of the crop."""
    zoom = seg.setdefault("zoom", 1.0)
    inside = [f for f in samples if seg["in"] <= f[0] <= seg["out"]]
    if inside and zoom > 1.0 and not seg.get("zoom_lock"):
        # keep the whole head (face box x ~1.7 with hair/hijab) under ~58% of the frame height, so text has room
        head = statistics.median(f[4] for f in inside) * 1.7
        cap = max(1.0, round(0.58 / head, 2))
        if zoom > cap:
            print(f"  {seg.get('id')}: zoom {zoom} -> {cap} (keeps room around the face; zoom_lock to override)")
            seg["zoom"] = zoom = cap
    if "cx" in seg and "cy" in seg:
        return
    if zoom <= 1.0 or not inside:
        seg.setdefault("cx", 0.5)
        seg.setdefault("cy", 0.5)
        return
    fx = statistics.median(f[1] for f in inside)
    fy = statistics.median(f[2] for f in inside)
    ch = min(info["width"], info["height"] * 9 / 16) * 16 / 9 / zoom
    seg.setdefault("cx", round(fx, 3))
    seg.setdefault("cy", round(fy + 0.10 * ch / info["height"], 3))


def encode(src, out, seg, info, nframes):
    x, y, cw, ch = crop_box(info, seg["zoom"], seg["cx"], seg["cy"])
    push = float(seg.get("push", 0))
    dur = nframes / FPS
    vf = ["setpts=PTS-STARTPTS", f"fps={FPS}", f"crop={cw}:{ch}:{x}:{y}"]
    if push > 0:
        # grow from 1080 to 1080*(1+push) wide over the segment, then crop the centre
        grow = f"(1+{push}*t/{dur:.4f})"
        vf += [f"scale=w='2*trunc({W}*{grow}/2)':h='2*trunc({H}*{grow}/2)':eval=frame:flags=bicubic",
               f"crop={W}:{H}:(iw-{W})/2:(ih-{H})/2"]
    else:
        vf += [f"scale={W}:{H}:flags=lanczos"]
    vf += ["setsar=1", "format=yuv420p"]
    af = (f"asetpts=PTS-STARTPTS,aresample={SR},atrim=0:{dur:.5f},apad=whole_dur={dur:.5f},"
          f"afade=t=in:d=0.012,afade=t=out:st={max(dur - 0.02, 0):.4f}:d=0.02")
    cmd = ["ffmpeg", "-v", "error", "-y", "-hwaccel", "auto", "-ss", f"{seg['in']:.3f}", "-i", str(src), "-t", f"{dur + 0.2:.3f}",
           "-map", "0:v:0", "-map", "0:a:0", "-vf", ",".join(vf), "-af", af, "-frames:v", str(nframes),
           "-c:v", "libx264", "-preset", "fast", "-crf", "16", "-g", str(FPS),
           "-c:a", "pcm_s16le", "-ac", "2", str(out)]
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        die(f"segment {seg['id']} failed: {p.stderr[-800:]}")


def face_in_frame(samples, seg, info):
    inside = [f for f in samples if seg["in"] <= f[0] <= seg["out"]] or samples
    if not inside:
        return None
    fx, fy, fw, fh = (statistics.median(f[i] for f in inside) for i in range(1, 5))
    x, y, cw, ch = crop_box(info, seg["zoom"], seg["cx"], seg["cy"])
    sw, sh = info["width"], info["height"]
    return {"cx": round((fx * sw - x) / cw, 4), "cy": round((fy * sh - y) / ch, 4),
            "w": round(fw * sw / cw, 4), "h": round(fh * sh / ch, 4)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("project")
    ap.add_argument("--push", type=float, default=0.0)
    a = ap.parse_args()
    proj = project_dir(a.project)
    edl = load_json(proj / "edl.json")
    clips = load_json(proj / "transcript.json")["clips"]
    work = proj / "work"

    segs, parts, frame = [], [], 0
    for i, seg in enumerate(edl):
        seg.setdefault("id", f"s{i + 1}")
        seg.setdefault("push", a.push)
        if seg["clip"] not in clips:
            die(f"segment {seg['id']}: unknown clip {seg['clip']}")
        c = clips[seg["clip"]]
        src = proj / "clips" / c["file"]
        info = ffprobe(src)
        if not 0 <= seg["in"] < seg["out"] <= info["duration"] + 0.05:
            die(f"segment {seg['id']}: in/out {seg['in']}-{seg['out']} outside the clip (0-{info['duration']:.2f})")
        auto_frame(seg, info, c.get("faces", []))
        n = round((seg["out"] - seg["in"]) * FPS)
        out = work / f"seg_{i:02d}.mkv"
        encode(src, out, seg, info, n)
        parts.append(out)
        start = frame / FPS
        words = [{"w": w["w"], "s": round(max(w["s"] - seg["in"], 0) + start, 3),
                  "e": round(min(w["e"], seg["out"]) - seg["in"] + start, 3)}
                 for w in c["words"] if seg["in"] - 0.05 <= (w["s"] + w["e"]) / 2 <= seg["out"]]
        segs.append({**seg, "start": round(start, 4), "end": round((frame + n) / FPS, 4),
                     "frame_start": frame, "frames": n, "words": words,
                     "face": face_in_frame(c.get("faces", []), seg, info)})
        frame += n
        print(f"{seg['id']}: {seg['clip']} {seg['in']:.2f}-{seg['out']:.2f} -> {start:.2f}s, {n} frames", flush=True)

    lst = work / "concat.txt"
    lst.write_text("".join(f"file '{p.name}'\n" for p in parts))
    p = subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy",
                        str(work / "aroll.mkv")], capture_output=True, text=True)
    if p.returncode != 0:
        die(f"concat failed: {p.stderr[-800:]}")
    save_json(proj / "timeline.json", {"fps": FPS, "frames": frame, "duration": round(frame / FPS, 4),
                                       "segments": segs})
    print(f"a-roll {frame / FPS:.2f}s ({frame} frames) -> {work / 'aroll.mkv'}")


if __name__ == "__main__":
    sys.exit(main())
