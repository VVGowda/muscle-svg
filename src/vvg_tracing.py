"""vvg_tracing - the shared potrace wrapper.

Two lessons are baked in here, both paid for in debugging time:

1. potrace traces BLACK pixels. Write a boolean mask as white-on-black and
   you get the exact complement of what you wanted. Hence the ~mask flip.

2. Upscale, blur, then re-threshold, in that order. The blur melts the pixel
   staircase so potrace draws flowing curves instead of thousands of tiny
   corners. Skip it and every outline comes out jagged. Blur without the
   re-threshold and potrace gets a grey image it cannot use.
"""
import os
import re
import subprocess

import numpy as np
from PIL import Image, ImageFilter

import vvg_config as C
import vvg_svgpath


def to_pbm(mask, path, scale=None, blur=None):
    """Write a boolean mask as a 1-bit PBM ready for potrace."""
    scale = C.TRACE_SCALE if scale is None else scale
    blur = C.BLUR if blur is None else blur
    h, w = mask.shape
    img = Image.fromarray((~mask * 255).astype(np.uint8), "L")
    if scale != 1:
        img = img.resize((w * scale, h * scale), Image.LANCZOS)
    if blur:
        img = img.filter(ImageFilter.GaussianBlur(blur))
    a = np.asarray(img)
    Image.fromarray(((a > 128).astype(np.uint8) * 255), "L").convert("1").save(path)
    return w * scale, h * scale


def run_potrace(pbm, svg, turd, alpha=1.0, opttol=0.2):
    subprocess.run(["potrace", pbm, "-s", "-o", svg,
                    "-t", str(int(turd)),
                    "-a", str(alpha),
                    "-O", str(opttol),
                    "-u", str(C.POTRACE_U)], check=True)


def paths_of(svg):
    return re.findall(r'<path[^>]*\sd="([^"]+)"', open(svg).read())


def trace_d(mask, tag, turd=4, scale=None, blur=None, alpha=1.0, opttol=0.2, nd=1):
    """Trace a mask, return one concatenated 'd' string in POTRACE space.

    The turd (despeckle) value is multiplied by scale squared because it is
    an area threshold, not a length. Forgetting the square either lets
    speckle through or eats real detail, depending on which way you forgot.
    """
    C.ensure_dirs()
    scale = C.TRACE_SCALE if scale is None else scale
    pbm = os.path.join(C.TMP, f"{tag}.pbm")
    svg = os.path.join(C.TMP, f"{tag}.svg")
    to_pbm(mask, pbm, scale, blur)
    run_potrace(pbm, svg, turd * scale * scale, alpha, opttol)
    ds = paths_of(svg)
    ds = [re.sub(r'-?\d+\.\d+', lambda m: '%g' % round(float(m.group(0)), nd), d) for d in ds]
    return " ".join(ds)


def trace_subpaths(mask, tag, turd=4, scale=None, blur=None):
    """Trace a mask and return parsed cubic subpaths already mapped back into
    SOURCE PIXEL space (y flipped, potrace units divided out)."""
    scale = C.TRACE_SCALE if scale is None else scale
    d = trace_d(mask, tag, turd=turd, scale=scale, blur=blur, nd=3)
    subs = vvg_svgpath.parse(d)
    k = C.POTRACE_U * scale
    uh = mask.shape[0] * k

    def f(p):
        return (p[0] / k, (uh - p[1]) / k)

    return [(f(start), [tuple(f(c) for c in seg) for seg in segs]) for start, segs in subs]
