"""vvg3 - render a numbered overlay so components can be named by eye.

No algorithm can know that component 13 is the right pectoral. This stage
paints every component a distinct random colour and prints its integer id at
the centroid, plus upper/mid/lower crops because the full-height image is
too tall to read numbers on.

You look at the crops and fill in vvg_names.py by hand. That is the only
manual step in the pipeline, a one-time cost per reference image.

Output: out/map_{view}.png and out/map_{view}_{upper,mid,lower}.png
"""
import json

import numpy as np
from PIL import Image, ImageDraw

import vvg_config as C

CROPS = {"upper": (0.00, 0.40), "mid": (0.33, 0.72), "lower": (0.65, 1.00)}


def render(view, info, font):
    L = np.load(f"{C.OUT}/lab_{view}.npy")
    comps = info[view]["comps"]
    ids = {c["id"] for c in comps}
    H, W = L.shape

    rng = np.random.default_rng(7)   # fixed seed: same colours every run
    colors = {i: tuple(int(x) for x in rng.integers(90, 245, 3)) for i in ids}
    out = np.full((H, W, 3), 255, np.uint8)
    for i in ids:
        out[L == i] = colors[i]

    img = Image.fromarray(out).resize((W * 2, H * 2), Image.NEAREST)
    d = ImageDraw.Draw(img)
    for c in comps:
        t, x, y = str(c["id"]), c["cx"] * 2, c["cy"] * 2
        # white halo so the number stays readable on any fill colour
        for dx in (-2, 0, 2):
            for dy in (-2, 0, 2):
                d.text((x + dx, y + dy), t, font=font, fill=(255, 255, 255), anchor="mm")
        d.text((x, y), t, font=font, fill=(0, 0, 0), anchor="mm")

    img.save(f"{C.OUT}/map_{view}.png")
    for name, (a, b) in CROPS.items():
        img.crop((0, int(H * 2 * a), W * 2, int(H * 2 * b))).save(f"{C.OUT}/map_{view}_{name}.png")
    print(f"{view}: {len(comps)} numbered")


if __name__ == "__main__":
    C.ensure_dirs()
    info = json.load(open(f"{C.OUT}/segments.json"))
    font = C.load_font(26)
    for v in ("front", "back"):
        render(v, info, font)
