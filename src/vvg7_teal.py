"""vvg7 - restyle the named regions in the teal palette.

Two variants, chosen on the command line:

  warped  - morph every region onto the teal body shape via vvg_warp.Warp.
            Matches the reference proportions but distorts the muscle
            drawing, most visibly across the shoulders and thighs.
  hybrid  - keep the source body geometry exactly as drawn, take only the teal
            palette and the teal head. Better anatomy, reference colours.
            This is the recommended output.

The teal look is a TWO-PASS DRAW per region:

    pass 1 (.edge)  fill LINE, stroke LINE, stroke-width G+S
    pass 2 (.m)     fill FILL, stroke FILL, stroke-width G

Stroking a filled path with its own fill colour fattens the shape outward by
half the stroke width. The wider dark pass underneath peeks out as a rim of
uniform thickness, and the leftover space between muscles reads as white.
stroke-linejoin: round is required - without it sharp corners throw long
miter spikes.

Beneath everything sits a white-filled, dark-stroked body silhouette. That
underlay is what makes the figure read as one body instead of a scatter of
loose strips.

Note the deliberately EMPTY <style></style> block in the output. CSS beats
presentation attributes in the cascade, so any fill declared in a stylesheet
would permanently block element.setAttribute("fill", ...). With all styling
in presentation attributes, both #chest-left { fill: red } and setAttribute
work. That is the difference between labelled and genuinely fillable.

Output: out/{teal,hybrid}-body-{view}.svg
"""
import os
import re
import sys

import numpy as np

import vvg_config as C
import vvg_masks as masks
import vvg_svgpath as svgpath
import vvg_tracing as tracing
from vvg_landmarks import analyze
from vvg_warp import Warp

# Joint markers copied from the teal reference (front only). Coordinates are
# teal source pixels. Dropped for the hybrid variant, whose different body
# geometry would put them in the wrong places.
JOINT_DOTS = [(166.3, 147.5, 6.0), (166.3, 187.2, 5.0),
              (92.6, 228.8, 3.25), (240.2, 229.2, 3.25),
              (144.4, 293.4, 3.0), (188.5, 293.4, 3.0),
              (139.0, 412.7, 3.25), (193.6, 412.7, 3.25),
              (132.2, 447.2, 3.75), (200.4, 447.2, 3.75)]

SIL_RE = r'<path id="silhouette-[a-z]+" class="region" fill="[^"]*" d="([^"]+)"'
GRP_RE = r'<g id="([a-z\-]+)">(.*?)\n    </g>'
PATH_RE = r'<path id="([^"]+)" class="[^"]*" fill="[^"]*" d="([^"]+)"'


def trace_teal_head(neck_stub=0):
    """Trace the teal front head. neck_stub extends the cut below the neck so
    the hybrid variant's join tucks behind the traced muscle neck."""
    tf = np.load(f"{C.OUT}/teal_front_sil.npy")
    lm = analyze(tf, "TEAL-front")
    m = tf.copy()
    m[lm["neck"] + 3 + neck_stub:] = False
    subs = tracing.trace_subpaths(m, "vvg7_head", turd=8, scale=8, blur=4.0)
    x0, x1, y0, y1 = masks.bbox(m)
    return subs, dict(x0=x0, x1=x1, y0=y0, y1=y1)


def build(view, variant, head_subs, head_box):
    warped = variant == "warped"

    src_mask = masks.silhouette(C.ART[view])
    lm_s = analyze(src_mask, f"ART-{view}")

    if warped:
        tgt = np.load(f"{C.OUT}/teal_{view}_sil.npy")
        lm_t = analyze(tgt, f"TEAL-{view}")
        W = Warp(src_mask, tgt, lm_s, lm_t)
        # normalise so front and back end up the same body height
        unit = C.UNIT * (C.TARGET_BODY_PX / (lm_t["sole"] - lm_t["crown"]))
        deform = W
    else:
        tgt, lm_t = src_mask, lm_s
        unit = (C.TARGET_BODY_PX * C.UNIT) / (lm_t["sole"] - lm_t["crown"])
        deform = lambda p: p

    # art potrace space -> art image pixel space
    src_h = src_mask.shape[0]
    b2i = lambda p: (p[0] / C.PT_DIV, src_h - p[1] / C.PT_DIV)
    xf = lambda p: tuple(v * unit for v in deform(b2i(p)))

    src_svg = open(f"{C.OUT}/body-{view}-regions.svg").read()
    sil_out = svgpath.emit(svgpath.parse(re.search(SIL_RE, src_svg).group(1)), xf)

    groups, order = {}, []
    for gm in re.finditer(GRP_RE, src_svg, re.S):
        gname, blk = gm.group(1), gm.group(2)
        if gname == "head":
            continue        # replaced by the teal head
        items = [(pid, svgpath.emit(svgpath.parse(d), xf))
                 for pid, d in re.findall(PATH_RE, blk)]
        if items:
            groups[gname] = items
            order.append(gname)

    # place the head to match this figure's own head box, aspect preserved
    hy0, hy1 = lm_t["crown"], lm_t["neck"] + 3
    hxs = np.where(tgt[hy0:hy1].any(0))[0]
    sc = (hy1 - hy0) / (head_box["y1"] - head_box["y0"] + 1)
    cx_t = (hxs.min() + hxs.max()) / 2.0
    cx_h = (head_box["x0"] + head_box["x1"]) / 2.0
    head_d = svgpath.emit(head_subs, lambda p: (
        ((p[0] - cx_h) * sc + cx_t) * unit,
        ((p[1] - head_box["y1"]) * sc + hy1) * unit))

    G, S = C.GAP_SPREAD, C.RIM
    E = f'fill="{C.TEAL_LINE}" stroke="{C.TEAL_LINE}" stroke-width="{G + S:g}" stroke-linejoin="round"'
    M = f'fill="{C.TEAL_FILL}" stroke="{C.TEAL_FILL}" stroke-width="{G:g}" stroke-linejoin="round"'
    Wt, Ht = tgt.shape[1] * unit, tgt.shape[0] * unit

    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {Wt} {Ht}"'
        f' width="{Wt / 2:.0f}" height="{Ht / 2:.0f}">',
        '  <style></style>',
        f'  <path id="body-outline" class="body" fill="#ffffff" stroke="{C.TEAL_LINE}"'
        f' stroke-width="{C.OUTLINE_W:g}" stroke-linejoin="round" d="{sil_out}"/>',
        '  <g id="g-head">',
        f'    <path class="edge" {E} d="{head_d}"/>',
        f'    <path id="head" class="m" {M} d="{head_d}"><title>head</title></path>',
        '  </g>',
    ]
    for gname in order:
        out.append(f'  <g id="{gname}">')
        for pid, d in groups[gname]:
            out.append(f'    <path class="edge" {E} d="{d}"/>')
            out.append(f'    <path id="{pid}" class="m {gname}" {M} d="{d}">'
                       f'<title>{pid.replace("-", " ")}</title></path>')
        out.append('  </g>')

    if warped and view == "front":
        out.append('  <g id="joint-markers">')
        for dx, dy, dr in JOINT_DOTS:
            out.append(f'    <circle cx="{dx * unit:.1f}" cy="{dy * unit:.1f}"'
                       f' r="{dr * unit:.1f}" fill="#ffffff" stroke="{C.TEAL_LINE}"'
                       f' stroke-width="{S * 0.55:g}"/>')
        out.append('  </g>')
    out.append('</svg>')

    prefix = "teal" if warped else "hybrid"
    fn = f"{C.OUT}/{prefix}-body-{view}.svg"
    open(fn, "w").write("\n".join(out))
    n = sum(len(v) for v in groups.values())
    print(f"{view} ({variant}): {n} regions -> {os.path.getsize(fn) // 1024} KB")


if __name__ == "__main__":
    C.ensure_dirs()
    variant = sys.argv[1] if len(sys.argv) > 1 else "hybrid"
    assert variant in ("warped", "hybrid"), "variant must be 'warped' or 'hybrid'"
    # hybrid needs a longer neck stub so the head join hides behind the neck muscle
    head_subs, head_box = trace_teal_head(neck_stub=0 if variant == "warped" else 18)
    for v in ("front", "back"):
        build(v, variant, head_subs, head_box)
