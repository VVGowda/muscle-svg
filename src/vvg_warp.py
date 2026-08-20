"""vvg_warp - row-conforming silhouette morph.

Maps every point inside a source silhouette to the matching point inside a
target silhouette of different proportions.

Vertical: piecewise-linear interpolation between the seven landmark anchors.

Horizontal: for the mapped output row, match the horizontal runs of the
source against those of the target. When the run counts agree (both rows are
left-arm / torso / right-arm, say) the run boundaries give a natural
piecewise-linear x mapping that keeps arms on arms. When the counts
disagree, fall back to mapping the overall extent. Outside the outermost
boundary, extrapolate with the local scale so nothing collapses to a point.

The raw grid is jittery because run boundaries jump a pixel from row to row.
So the grid is built subsampled (step 3), gaussian smoothed, and bilinearly
resampled on lookup. That smoothing is why warped muscle outlines read as
curves instead of wobble.
"""
import numpy as np
from scipy import ndimage

from vvg_landmarks import runs

# Armpit and knee are left out on purpose: both are unreliable, and anchoring
# on them put visible kinks in the thigh and upper arm.
ANCHORS = ["crown", "neck", "shoulder", "hand", "crotch", "ankle", "sole"]


class Warp:
    def __init__(self, src, tgt, lm_s, lm_t, step=3, sigma=2.0):
        self.step = step
        Hs, Ws = src.shape
        Ht, Wt = tgt.shape
        ys = np.arange(0, Hs, step)
        xs = np.arange(0, Ws, step)
        self.ys, self.xs = ys, xs

        sy = np.array([lm_s[k] for k in ANCHORS], float)
        ty = np.array([lm_t[k] for k in ANCHORS], float)

        src_runs = [runs(src[y]) for y in range(Hs)]
        tgt_runs = [runs(tgt[y]) for y in range(Ht)]
        t_nonempty = np.array([len(r) > 0 for r in tgt_runs])
        t_idx = np.where(t_nonempty)[0]

        GX = np.zeros((len(ys), len(xs)))
        GY = np.zeros((len(ys), len(xs)))

        for j, y in enumerate(ys):
            yt = float(np.interp(y, sy, ty))
            yt_i = int(np.clip(round(yt), 0, Ht - 1))
            if not t_nonempty[yt_i] and len(t_idx):
                yt_i = int(t_idx[np.argmin(np.abs(t_idx - yt_i))])

            rs, rt = src_runs[y], tgt_runs[yt_i]
            if not rs or not rt:
                GX[j] = (xs - Ws / 2) * 0.4 + Wt / 2
                GY[j] = yt
                continue

            if len(rs) == len(rt):
                ks = [v for a, b in rs for v in (a, b)]
                kt = [v for a, b in rt for v in (a, b)]
            else:
                ks = [rs[0][0], rs[-1][1]]
                kt = [rt[0][0], rt[-1][1]]

            ks = np.array(ks, float)
            kt = np.array(kt, float)
            keep = np.concatenate([[True], np.diff(ks) > 0])
            ks, kt = ks[keep], kt[keep]
            if len(ks) < 2:
                ks = np.array([ks[0] - 1, ks[0] + 1])
                kt = np.array([kt[0] - 1, kt[0] + 1])

            sc_lo = (kt[1] - kt[0]) / max(ks[1] - ks[0], 1e-6)
            sc_hi = (kt[-1] - kt[-2]) / max(ks[-1] - ks[-2], 1e-6)
            v = np.interp(xs, ks, kt)
            v = np.where(xs < ks[0], kt[0] + (xs - ks[0]) * sc_lo, v)
            v = np.where(xs > ks[-1], kt[-1] + (xs - ks[-1]) * sc_hi, v)
            GX[j] = v
            GY[j] = yt

        # The vertical grid is smoothed only along y. Smoothing it across x
        # would shear the figure.
        self.GX = ndimage.gaussian_filter(GX, sigma, mode="nearest")
        self.GY = ndimage.gaussian_filter(GY, (sigma, 0), mode="nearest")

    def __call__(self, p):
        """Bilinear lookup. Called on every Bezier control point."""
        x, y = p
        fy = np.clip(y / self.step, 0, len(self.ys) - 1.001)
        fx = np.clip(x / self.step, 0, len(self.xs) - 1.001)
        j, i = int(fy), int(fx)
        dy, dx = fy - j, fx - i

        def bil(G):
            return (G[j, i] * (1 - dx) * (1 - dy) + G[j, i + 1] * dx * (1 - dy) +
                    G[j + 1, i] * (1 - dx) * dy + G[j + 1, i + 1] * dx * dy)

        return (float(bil(self.GX)), float(bil(self.GY)))
