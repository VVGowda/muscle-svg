"""vvg8 - standalone: auto-trace the photoreal anatomy renders.

A completely different problem from vvg1-vvg7. The renders have continuous
gradients and fibre striations, so there are no flat regions to find
connected components in, and no way to recover named muscles from them.

Approach - layered colour quantization:

  1. isolate the figure by saturation + luminance, filling only SMALL holes
     so the gap between the legs stays open (a global binary_fill_holes
     bridges it, because the arms and torso enclose it from above; that was
     a real shipped bug, a solid brown wedge between the legs)
  2. crop to the figure, upscale 3x Lanczos, median filter against JPEG ringing
  3. knock the background to pure white so it becomes its own palette entry
  4. quantize to a 16-colour adaptive palette (MEDIANCUT, no dither)
  5. trace each palette colour as its own layer
  6. stack largest-area-first over a base of the dominant tone, each mask
     closed and dilated 1px so no white seams show at the joins

The result looks like the reference, but the layers are shading bands, not
muscles. There is no #biceps-left here - that is what vvg1-vvg7 are for.

No upscale inside the trace call here: the image is already upscaled 3x, so
tracing runs at that resolution with just a light 0.8 blur.

Output: out/render-{view}.svg
"""
import os
import re
import subprocess

import numpy as np
from PIL import Image, ImageFilter
from scipy import ndimage

import vvg_config as C
import vvg_masks as masks
import vvg_svgpath as svgpath

K3 = np.ones((3, 3))


def pick(mask, which):
    """Select one figure, return (mask, bbox). which: left | right | largest."""
    lab, n = ndimage.label(mask)
    sizes = ndimage.sum(mask, lab, range(1, n + 1))
    order = np.argsort(sizes)[::-1] + 1
    cands = [i for i in order[:3] if sizes[i - 1] > 8000]
    boxes = {}
    for i in cands:
        ys, xs = np.where(lab == i)
        boxes[i] = (int(xs.min()), int(xs.max()), int(ys.min()), int(ys.max()))
    if which == "left":
        k = min(boxes, key=lambda i: boxes[i][0])
    elif which == "right":
        k = max(boxes, key=lambda i: boxes[i][0])
    else:
        k = cands[0]
    return (lab == k), boxes[k]


def trace_bool(mask, tag):
    """Trace at native resolution, return a 'd' string already in image px."""
    h, w = mask.shape
    pbm, svg = f"{C.TMP}/{tag}.pbm", f"{C.TMP}/{tag}.svg"
    img = Image.fromarray((~mask * 255).astype(np.uint8), "L") \
               .filter(ImageFilter.GaussianBlur(0.8))
    a = np.asarray(img)
    Image.fromarray(((a > 128).astype(np.uint8) * 255), "L").convert("1").save(pbm)
    subprocess.run(["potrace", pbm, "-s", "-o", svg,
                    "-t", "2", "-a", "1.2", "-O", "0.25", "-u", str(C.POTRACE_U)],
                   check=True)
    d = " ".join(re.findall(r'<path[^>]*\sd="([^"]+)"', open(svg).read()))
    if not d.strip():
        return None
    uh = h * C.POTRACE_U
    return svgpath.emit(svgpath.parse(d),
                        lambda p: (p[0] / C.POTRACE_U, (uh - p[1]) / C.POTRACE_U))


def build(view, which):
    C.ensure_dirs()
    im = np.asarray(Image.open(C.RENDER[view]).convert("RGB")).astype(int)
    m, (x0, x1, y0, y1) = pick(masks.figure_mask(Image.open(C.RENDER[view])), which)

    p = C.AT_PAD
    x0, y0 = max(0, x0 - p), max(0, y0 - p)
    x1 = min(im.shape[1] - 1, x1 + p)
    y1 = min(im.shape[0] - 1, y1 + p)
    sub, sm = im[y0:y1 + 1, x0:x1 + 1], m[y0:y1 + 1, x0:x1 + 1]

    U = C.AT_UPSCALE
    pil = Image.fromarray(sub.astype(np.uint8))
    W, H = pil.size
    pil = pil.resize((W * U, H * U), Image.LANCZOS).filter(ImageFilter.MedianFilter(3))
    big = np.asarray(Image.fromarray((sm * 255).astype(np.uint8))
                     .resize((W * U, H * U), Image.LANCZOS)) > 110
    big = ndimage.binary_closing(big, K3)

    arr = np.asarray(pil).astype(np.uint8).copy()
    arr[~big] = 255
    q = Image.fromarray(arr).quantize(colors=C.AT_COLORS, method=Image.MEDIANCUT,
                                      dither=Image.NONE)
    idx = np.asarray(q)
    pal = np.asarray(q.getpalette()[:C.AT_COLORS * 3]).reshape(-1, 3)

    counts = sorted(((int((idx == i).sum()), i) for i in range(C.AT_COLORS)), reverse=True)
    layers = []
    for cnt, i in counts:
        if cnt < C.AT_MIN_PX or pal[i].min() > 246:
            continue
        mk = ndimage.binary_closing((idx == i) & big, K3)
        mk = ndimage.binary_dilation(mk, K3)
        if mk.sum() < C.AT_MIN_PX:
            continue
        layers.append((cnt, "#%02x%02x%02x" % tuple(pal[i]), mk))

    Wo, Ho = arr.shape[1], arr.shape[0]
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {Wo} {Ho}"'
           f' width="{Wo // U}" height="{Ho // U}">',
           '  <style></style>',
           f'  <rect width="{Wo}" height="{Ho}" fill="#ffffff"/>']

    base = trace_bool(ndimage.binary_dilation(big, K3), f"vvg8_{view}_base")
    if base:
        out.append(f'  <path id="body-base" fill="{layers[0][1]}" d="{base}"/>')
    for n, (_, col, mk) in enumerate(sorted(layers, key=lambda t: -t[0])):
        d = trace_bool(mk, f"vvg8_{view}_l{n}")
        if d:
            out.append(f'  <path id="tone-{n:02d}" fill="{col}" d="{d}"/>')
    out.append('</svg>')

    fn = f"{C.OUT}/render-{view}.svg"
    open(fn, "w").write("\n".join(out))
    print(f"{view}: {len(layers)} tone layers -> {os.path.getsize(fn) // 1024} KB"
          f" ({Wo // U}x{Ho // U})")


if __name__ == "__main__":
    build("front", "left")       # the front render is a two-up image; take the left
    build("back", "largest")
