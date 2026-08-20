"""vvg4 - emit the named, individually fillable region SVGs.

Each component is dilated 1px (adjacent regions then overlap slightly, so no
white hairline shows at the seams), traced on its own, and written as its
own <path> with a unique id, inside a <g> named after its muscle group.

Naming: {group}-{side} when a group has one region on that side, otherwise
{group}-{side}-{n} numbered top-to-bottom. Sides are ANATOMICAL: on the
front view, viewer-left is the subject's RIGHT.

Output: out/body-{view}-regions.svg, out/names_{view}.json
"""
import json
import os
from collections import defaultdict

import numpy as np
from PIL import Image
from scipy import ndimage

import vvg_config as C
import vvg_masks as masks
import vvg_tracing as tracing
from vvg_names import MAPS

DIL = np.ones((3, 3), bool)


def assign_names(comps, nmap):
    """Group components by (group, side) and give each one a unique id string."""
    bucket = defaultdict(list)
    for c in comps:
        bucket[nmap[c["id"]]].append(c)

    names, groups = {}, defaultdict(list)
    for (grp, side), cs in bucket.items():
        cs.sort(key=lambda c: (c["cy"], c["cx"]))
        base = grp if side is None else f"{grp}-{side}"
        for i, c in enumerate(cs, 1):
            names[c["id"]] = base if len(cs) == 1 else f"{base}-{i}"
            groups[grp].append(c["id"])
    return names, groups


def build(view, info):
    nmap = MAPS[view]
    comps = info[view]["comps"]
    missing = [c["id"] for c in comps if c["id"] not in nmap]
    assert not missing, f"{view}: unmapped component ids {missing} - add them to vvg_names.py"

    lab_px = masks.classify_palette(C.ART[view])
    L = np.load(f"{C.OUT}/lab_{view}.npy")
    W, H = Image.open(C.ART[view]).size
    names, groups = assign_names(comps, nmap)

    sil_d = tracing.trace_d(masks.body_mask(lab_px), f"vvg4_{view}_sil", turd=20)
    line_d = tracing.trace_d(masks.line_mask(lab_px), f"vvg4_{view}_line", turd=6)

    uw, uh = W * C.TRACE_SCALE, H * C.TRACE_SCALE
    tr = f"translate(0,{uh}) scale(0.1,-0.1)"
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {uw} {uh}" width="{W}" height="{H}">',
        '  <style>',
        f'    .region {{ fill: {C.ART_FILL}; transition: fill .15s; }}',
        f'    .lines  {{ fill: {C.ART_LINE}; pointer-events: none; }}',
        '  </style>',
        f'  <g transform="{tr}">',
        f'    <path id="silhouette-{view}" class="region" fill="{C.ART_FILL}" d="{sil_d}"/>',
    ]
    for grp in sorted(groups):
        out.append(f'    <g id="{grp}">')
        for cid in sorted(groups[grp], key=lambda i: names[i]):
            m = ndimage.binary_dilation(L == cid, DIL, iterations=1)
            d = tracing.trace_d(m, f"vvg4_{view}_{cid}")
            label = names[cid].replace("-", " ")
            out.append(f'      <path id="{names[cid]}" class="region {grp}"'
                       f' fill="{C.ART_FILL}" d="{d}"><title>{label}</title></path>')
        out.append('    </g>')
    out.append(f'    <path class="lines" fill="{C.ART_LINE}" d="{line_d}"/>')
    out += ['  </g>', '</svg>']

    fn = f"{C.OUT}/body-{view}-regions.svg"
    open(fn, "w").write("\n".join(out))
    json.dump({names[c["id"]]: nmap[c["id"]][0] for c in comps},
              open(f"{C.OUT}/names_{view}.json", "w"), indent=1)
    print(f"{view}: {len(names)} regions in {len(groups)} groups, {os.path.getsize(fn) // 1024} KB")


if __name__ == "__main__":
    C.ensure_dirs()
    info = json.load(open(f"{C.OUT}/segments.json"))
    for v in ("front", "back"):
        build(v, info)
