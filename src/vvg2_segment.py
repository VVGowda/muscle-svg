"""vvg2 - find the individual muscle regions.

The reference art already separates muscles with white gaps, so the muscles
are literally the connected components of the fill colour. No drawing, no
segmentation model.

  1. isolate the muscle fill colour (linework excluded)
  2. binary_opening 3x3 to break thin accidental bridges between muscles
  3. scipy.ndimage.label with 4-connectivity
  4. drop components under MIN_AREA px

Gives 90 components on the front and 67 on the back. They are anonymous
integers at this point - naming happens in vvg3.

Output: out/lab_{view}.npy (label array), out/segments.json (metadata)
"""
import json

import numpy as np
from PIL import Image
from scipy import ndimage

import vvg_config as C
import vvg_masks as masks

# 4-connectivity on purpose: two muscles touching only at a diagonal pixel
# must NOT merge into one component, and in this art they often do touch
# diagonally at their tips.
CONN4 = np.array([[0, 1, 0], [1, 1, 1], [0, 1, 0]])


def segment(view):
    lab_px = masks.classify_palette(C.ART[view])
    fill = masks.fill_mask(lab_px)

    L, n = ndimage.label(fill, structure=CONN4)
    areas = ndimage.sum(np.ones_like(L), L, range(1, n + 1))
    keep = [i + 1 for i in range(n) if areas[i] >= C.MIN_AREA]
    cents = ndimage.center_of_mass(np.ones_like(L), L, keep)

    comps = []
    for k, (cy, cx) in zip(keep, cents):
        ys, xs = np.where(L == k)
        comps.append(dict(id=int(k), area=int(areas[k - 1]),
                          cx=round(float(cx), 1), cy=round(float(cy), 1),
                          x0=int(xs.min()), x1=int(xs.max()),
                          y0=int(ys.min()), y1=int(ys.max())))
    # top-to-bottom, left-to-right: keeps the numbered overlay readable
    comps.sort(key=lambda c: (c["cy"], c["cx"]))

    np.save(f"{C.OUT}/lab_{view}.npy", L.astype(np.int32))
    H, W = L.shape
    print(f"{view}: kept {len(comps)} of {n} components")
    return dict(W=W, H=H, comps=comps)


if __name__ == "__main__":
    C.ensure_dirs()
    info = {v: segment(v) for v in ("front", "back")}
    json.dump(info, open(f"{C.OUT}/segments.json", "w"), indent=1)
