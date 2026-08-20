"""vvg_landmarks - body landmark detection by horizontal run analysis.

No pose model needed. On a clean silhouette, scan every row and look at the
runs of filled pixels. The count and width of those runs change in
characteristic ways at body transitions:

  * one run becomes three where the arms leave the torso
  * the torso run pinches hard at the neck
  * one run becomes two at the crotch
  * the leg run hits a local minimum at the ankle

Seven landmarks came out reliable enough to anchor a warp: crown, neck,
shoulder, hand, crotch, ankle, sole. Armpit and knee are detected too but
they are noisy - feeding them to the warp made it worse, so the warp
ignores them.
"""
import numpy as np


def runs(row):
    """Contiguous runs of True in a 1-D boolean row -> [(start, end), ...]."""
    idx = np.where(row)[0]
    if len(idx) == 0:
        return []
    brk = np.where(np.diff(idx) > 1)[0]
    out, s = [], idx[0]
    for b in brk:
        out.append((s, idx[b]))
        s = idx[b + 1]
    out.append((s, idx[-1]))
    return out


def analyze(mask, tag=None, verbose=True):
    """Detect landmarks on a silhouette mask. Returns a dict of row indices."""
    ys = np.where(mask.any(1))[0]
    y0, y1 = int(ys.min()), int(ys.max())
    Hb = y1 - y0

    W = np.array([mask[y].sum() for y in range(mask.shape[0])])
    allruns = [runs(mask[y]) for y in range(mask.shape[0])]
    nr = np.array([len(r) for r in allruns])
    ext = np.array([(r[0][0], r[-1][1]) if r else (0, 0) for r in allruns])

    # neck: narrowest row in the head-to-shoulder band
    band = range(y0 + int(Hb * 0.08), y0 + int(Hb * 0.22))
    y_neck = min(band, key=lambda y: W[y])

    # shoulder: first row below the neck at least 2.2x the neck width
    y_sh = next((y for y in range(y_neck, y0 + int(Hb * 0.35))
                 if W[y] >= 2.2 * W[y_neck]), y_neck + 10)

    # armpit: first row below the shoulder with 3+ runs (noisy, warp skips it)
    y_pit = next((y for y in range(y_sh, y0 + int(Hb * 0.6)) if nr[y] >= 3), y_sh + 30)

    # hand: row of maximum total horizontal extent (arms are widest there)
    y_hand = int(np.argmax(ext[:, 1] - ext[:, 0]))

    # crotch: searching upward, the lowest row where the legs still merge
    lo, hi = y0 + int(Hb * 0.45), y0 + int(Hb * 0.75)
    y_crotch = next((y for y in range(hi, lo, -1)
                     if nr[y] <= 2 and nr[y + 1] >= 2 and len(allruns[y]) < len(allruns[y + 3])), None)
    if y_crotch is None:
        y_crotch = next((y for y in range(lo, hi) if nr[y] == 2), (lo + hi) // 2)

    # ankle: narrowest leg row near the bottom
    b2 = range(y0 + int(Hb * 0.86), y0 + int(Hb * 0.97))
    y_ank = min(b2, key=lambda y: W[y])

    # knee: narrowest row between crotch and ankle, biased low (noisy, warp skips it)
    b3 = range(y_crotch + int((y_ank - y_crotch) * 0.35),
               y_crotch + int((y_ank - y_crotch) * 0.75))
    y_knee = min(b3, key=lambda y: W[y])

    lm = dict(crown=y0, neck=int(y_neck), shoulder=int(y_sh), armpit=int(y_pit),
              hand=int(y_hand), crotch=int(y_crotch), knee=int(y_knee),
              ankle=int(y_ank), sole=y1)
    if verbose and tag:
        print(f"{tag} H={Hb} {lm} | headfrac={(lm['neck'] - y0) / Hb:.3f}")
    return lm
