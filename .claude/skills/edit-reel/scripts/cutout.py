"""Cut the speaker out of the background for the effects that need it (text behind the head, new backgrounds,
outlines, dolly zoom...). Only the frames inside those effects are processed.

    cutout.py <project>

Model: MODNet portrait matting (Apache 2.0), run with ONNX Runtime; downloaded once into assets/models/.
Writes work/matte.npy (uint8, frames x 896 x 512) and work/matte.json (which reel frames are stored where).
"""
import json
import subprocess
import sys
import time
import urllib.request

import numpy as np

from common import FPS, H, SK, W, die, load_json, project_dir
from effects import load_effects

MODEL_URL = "https://huggingface.co/Xenova/modnet/resolve/main/onnx/model.onnx"
MODEL = SK / "assets" / "models" / "modnet.onnx"
MH, MW = 896, 512           # model input (9:16, multiple of 32)
MARGIN = 0.4                # seconds of matte kept around each effect for its in/out animation


def model():
    if not MODEL.exists():
        MODEL.parent.mkdir(parents=True, exist_ok=True)
        print("downloading the cutout model (25 MB, once)...", flush=True)
        urllib.request.urlretrieve(MODEL_URL, MODEL)
    import onnxruntime as ort
    opts = ort.SessionOptions()
    opts.intra_op_num_threads = 0
    providers = [p for p in ("CoreMLExecutionProvider", "CPUExecutionProvider") if p in ort.get_available_providers()]
    return ort.InferenceSession(str(MODEL), opts, providers=providers)


def needed_frames(effects, total):
    want = np.zeros(total, bool)
    for e in effects:
        if e.needs_matte:
            a = max(0, int((e.start - MARGIN) * FPS))
            b = min(total, int((e.end + MARGIN) * FPS) + 1)
            want[a:b] = True
    return np.flatnonzero(want)


def main():
    proj = project_dir(sys.argv[1]) if len(sys.argv) > 1 else die("usage: cutout.py <project>")
    tl = load_json(proj / "timeline.json")
    plan = load_json(proj / "plan.json")
    frames = needed_frames(load_effects(plan, tl, proj), tl["frames"])
    work = proj / "work"
    index_path = work / "matte.json"
    if not len(frames):
        index_path.write_text(json.dumps({"frames": []}))
        print("no effect needs a cutout; nothing to do")
        return
    old = json.loads(index_path.read_text()) if index_path.exists() else {}
    if old.get("frames") == frames.tolist() and (work / "matte.npy").exists():
        print("cutout already up to date")
        return
    sess = model()
    name = sess.get_inputs()[0].name
    store = np.lib.format.open_memmap(work / "matte.npy", mode="w+", dtype=np.uint8, shape=(len(frames), MH, MW))
    # decode only the needed stretches of the a-roll, at model resolution
    runs, start = [], frames[0]
    for a, b in zip(frames, frames[1:]):
        if b != a + 1:
            runs.append((start, a))
            start = b
    runs.append((start, frames[-1]))
    t0, row, prev = time.time(), 0, None
    for a, b in runs:
        n = b - a + 1
        p = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{a / FPS:.4f}", "-i", str(work / "aroll.mkv"),
                            "-frames:v", str(n), "-vf", f"scale={MW}:{MH}:flags=area", "-f", "rawvideo",
                            "-pix_fmt", "rgb24", "-"], capture_output=True, check=True)
        clip = np.frombuffer(p.stdout, np.uint8).reshape(-1, MH, MW, 3)
        prev = None
        for i in range(n):
            img = clip[min(i, len(clip) - 1)].astype(np.float32)
            x = ((img / 255 - 0.5) / 0.5).transpose(2, 0, 1)[None]
            m = sess.run(None, {name: x})[0][0, 0]
            prev = m if prev is None else 0.65 * m + 0.35 * prev      # calm frame-to-frame flicker
            store[row] = np.clip(prev * 255, 0, 255).astype(np.uint8)
            row += 1
            if row % 60 == 0:
                left = (time.time() - t0) / row * (len(frames) - row)
                print(f"  cutout {row}/{len(frames)} frames, ~{left / 60:.1f} min left", flush=True)
    store.flush()
    index_path.write_text(json.dumps({"frames": frames.tolist(), "size": [MW, MH], "out": [W, H]}))
    print(f"cutout done: {len(frames)} frames in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    sys.exit(main())
