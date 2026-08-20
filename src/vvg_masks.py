"""vvg_masks - turning source images into boolean masks.

Three different mask problems show up in this project, and each one wants a
different approach:

  * flat two-colour line art  -> nearest-palette-colour classification
  * flat teal silhouette      -> non-white + close + fill + largest component
  * photoreal render          -> saturation/luminance + size-limited hole fill

They live together in this file so the differences stay visible.
"""
import numpy as np
from PIL import Image
from scipy import ndimage

import vvg_config as C


def load_rgb(path):
    return np.asarray(Image.open(path).convert("RGB")).astype(int)


# ---------------------------------------------------------------------------
# flat two-colour line art
# ---------------------------------------------------------------------------
def classify_palette(path, palette=None):
    """Label every pixel by its nearest palette colour.

    Returns an int array indexed like the palette list. For the line art that
    means 0 = white, 1 = muscle fill, 2 = linework.
    """
    palette = C.ART_RGB if palette is None else palette
    a = load_rgb(path)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    d = [((r - c[0]) ** 2 + (g - c[1]) ** 2 + (b - c[2]) ** 2) for c in palette]
    return np.argmin(np.stack(d), axis=0)


def fill_mask(lab):
    """Muscle fill only, opened 3x3 so touching muscles separate cleanly."""
    return ndimage.binary_opening(lab == 1, np.ones((3, 3)))


def line_mask(lab):
    return lab == 2


def body_mask(lab):
    return lab != 0


# ---------------------------------------------------------------------------
# flat silhouette (teal reference, or the line art as one body)
# ---------------------------------------------------------------------------
def silhouette(path, thresh=720):
    """Non-white pixels, closed and hole-filled, largest component only."""
    a = load_rgb(path)
    m = a.sum(2) < thresh
    m = ndimage.binary_closing(m, np.ones((5, 5)))
    m = ndimage.binary_fill_holes(m)
    lab, n = ndimage.label(m)
    if n > 1:
        sizes = ndimage.sum(m, lab, range(1, n + 1))
        m = lab == (int(np.argmax(sizes)) + 1)
    return ndimage.binary_fill_holes(m)


# ---------------------------------------------------------------------------
# photoreal render
# ---------------------------------------------------------------------------
def _fill_small_holes(mask, max_area):
    """Fill interior holes below max_area, and only those.

    Never run a global binary_fill_holes on a whole figure: the gap between
    the legs is enclosed by the legs and the crotch, so a global fill paints
    it solid. Capping by hole area closes real speckle while the leg gap
    stays open. Holes touching the image border are skipped too.
    """
    holes = ~mask
    lab, n = ndimage.label(holes)
    if n == 0:
        return mask
    out = mask.copy()
    border = set(lab[0].tolist()) | set(lab[-1].tolist()) \
        | set(lab[:, 0].tolist()) | set(lab[:, -1].tolist())
    areas = ndimage.sum(holes, lab, range(1, n + 1))
    for i in range(1, n + 1):
        if i in border:
            continue
        if areas[i - 1] < max_area:
            out[lab == i] = True
    return out


def figure_mask(path_or_img):
    """Pull the figure out of a photoreal render on a near-white background."""
    if isinstance(path_or_img, str):
        a = load_rgb(path_or_img)
    else:
        a = np.asarray(path_or_img.convert("RGB")).astype(int)
    mx, mn = a.max(2), a.min(2)
    sat = mx - mn
    lum = a.mean(2)
    m = (sat > 22) | (lum < 205)
    m = ndimage.binary_closing(m, np.ones((5, 5)))
    return _fill_small_holes(m, C.AT_HOLE_PX)


def pick_component(mask, which="largest"):
    """Keep one connected component: 'left', 'right', or 'largest' by area."""
    lab, n = ndimage.label(mask)
    if n <= 1:
        return mask
    sizes = ndimage.sum(mask, lab, range(1, n + 1))
    cand = [i for i in range(1, n + 1) if sizes[i - 1] > 0.05 * sizes.max()]
    if which == "largest":
        k = int(np.argmax(sizes)) + 1
    else:
        xs = {i: np.where(lab == i)[1].mean() for i in cand}
        k = min(xs, key=xs.get) if which == "left" else max(xs, key=xs.get)
    return lab == k


def bbox(mask):
    ys, xs = np.where(mask)
    return int(xs.min()), int(xs.max()), int(ys.min()), int(ys.max())
