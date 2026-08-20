"""vvg6 - extract the teal style-reference silhouettes.

The teal art is the target body shape for the warp, and its front figure
supplies the head. This stage also prints scanline widths at key height
fractions and writes a coordinate-gridded overlay - both were essential for
eyeballing whether the warp was landing where it should.

Output: out/teal_{view}_sil.npy, out/teal_{view}_grid.png
"""
import numpy as np
from PIL import Image, ImageDraw

import vvg_config as C
import vvg_masks as masks

FRACS = [0.0, 0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
TEAL_RGB = np.array([95, 179, 166])


def extract(view, font):
    body = masks.silhouette(C.TEAL[view])
    np.save(f"{C.OUT}/teal_{view}_sil.npy", body)

    H, W = body.shape
    x0, x1, y0, y1 = masks.bbox(body)
    print(f"{view}: img {W}x{H} | bbox x {x0}..{x1} y {y0}..{y1}"
          f" | body {x1 - x0} x {y1 - y0}")
    for fr in FRACS:
        yy = min(int(y0 + (y1 - y0) * fr), H - 1)
        row = np.where(body[yy])[0]
        if len(row):
            print(f"    y={yy} ({fr:.2f}) x {row.min()}..{row.max()}")

    ov = Image.fromarray(np.where(body[..., None], TEAL_RGB, 255).astype(np.uint8))
    ov = ov.resize((W * 2, H * 2), Image.NEAREST)
    d = ImageDraw.Draw(ov)
    for x in range(0, W, 20):
        d.line([(x * 2, 0), (x * 2, H * 2)], fill=(220, 220, 220))
        d.text((x * 2 + 2, 2), str(x), font=font, fill=(200, 0, 0))
    for y in range(0, H, 20):
        d.line([(0, y * 2), (W * 2, y * 2)], fill=(220, 220, 220))
        d.text((2, y * 2 + 2), str(y), font=font, fill=(0, 0, 200))
    ov.save(f"{C.OUT}/teal_{view}_grid.png")


if __name__ == "__main__":
    C.ensure_dirs()
    font = C.load_font(13)
    for v in ("front", "back"):
        extract(v, font)
