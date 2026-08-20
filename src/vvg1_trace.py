"""vvg1 - trace the flat reference art into plain SVG.

Two layers per view: the whole body silhouette in the fill colour and the
linework on top in the line colour. No named regions yet. This stage exists to
prove the trace parameters are right before spending time on segmentation.

Output: out/body-{front,back}.svg, out/body-front-back.svg
"""
import os
import re

import vvg_config as C
import vvg_masks as masks
import vvg_tracing as tracing


def build_view(view):
    lab = masks.classify_palette(C.ART[view])
    from PIL import Image
    W, H = Image.open(C.ART[view]).size

    body_d = tracing.trace_d(masks.body_mask(lab), f"vvg1_{view}_body", turd=20)
    line_d = tracing.trace_d(masks.line_mask(lab), f"vvg1_{view}_line", turd=6)

    uw, uh = W * C.TRACE_SCALE, H * C.TRACE_SCALE
    # the negative y scale flips potrace's y-up into SVG's y-down
    tr = f"translate(0,{uh}) scale(0.1,-0.1)"

    svg = "\n".join([
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {uw} {uh}" width="{W}" height="{H}">',
        f'  <g id="body-{view}" transform="{tr}" fill="{C.ART_FILL}" fill-rule="evenodd">',
        f'    <path d="{body_d}"/>',
        '  </g>',
        f'  <g id="detail-{view}" transform="{tr}" fill="{C.ART_LINE}" fill-rule="evenodd">',
        f'    <path d="{line_d}"/>',
        '  </g>',
        '</svg>',
    ])
    fn = f"{C.OUT}/body-{view}.svg"
    open(fn, "w").write(svg)
    print(f"{view}: {os.path.getsize(fn) // 1024} KB")
    return svg


def combine(svgs):
    def inner(t):
        return t[t.index(">", t.index("<svg")) + 1: t.rindex("</svg>")]

    m = re.search(r'viewBox="0 0 ([\d.]+) ([\d.]+)"', svgs["front"])
    W, H = float(m.group(1)), float(m.group(2))
    gap = W * 0.12
    tot = W * 2 + gap
    out = "\n".join([
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {tot:g} {H:g}"'
        f' width="{int(tot / C.PT_DIV)}" height="{int(H / C.PT_DIV)}">',
        '  <g id="front">' + inner(svgs["front"]) + '  </g>',
        f'  <g id="back" transform="translate({W + gap:g},0)">' + inner(svgs["back"]) + '  </g>',
        '</svg>',
    ])
    fn = f"{C.OUT}/body-front-back.svg"
    open(fn, "w").write(out)
    print(f"combined: {os.path.getsize(fn) // 1024} KB")


if __name__ == "__main__":
    C.ensure_dirs()
    combine({v: build_view(v) for v in ("front", "back")})
