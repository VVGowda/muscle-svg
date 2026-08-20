# Implementation notes

Everything in here was learned the hard way. Read this before changing any
parameter.

## potrace traces BLACK pixels

A boolean mask written as white-on-black gives you the exact complement of
what you want - the figure becomes a hole and the background becomes the
shape. In practice you get a scatter of unrecognisable fragments.

So every mask is inverted before writing the PBM:

```python
Image.fromarray((~mask * 255).astype(np.uint8), "L")
```

This broke the very first autotrace run, completely.

## Upscale, blur, then re-threshold

The sequence in `vvg_tracing.to_pbm` is deliberate and order-dependent:

1. Lanczos upscale 3-8x
2. Gaussian blur, sigma 0.8-4.0
3. Re-threshold at >128
4. Convert to PIL mode `"1"`

The blur melts the pixel staircase so potrace emits flowing curves instead
of thousands of micro-corners. Trace without it and edges are visibly
jagged. Blur without the re-threshold and potrace gets a grey image it
cannot use.

Sigma scales with the upscale factor. At 3x use about 1.2; at 8x use
3.0-4.0.

## potrace flags

| Flag | Value | Effect |
|---|---|---|
| `-s` | | SVG output |
| `-t` | `turd x scale^2` | Despeckle. **Must scale with the square of the upscale factor** - it is an area, not a length. |
| `-a` | 1.0-1.2 | Corner threshold. Higher rounds corners harder. |
| `-O` | 0.2-0.25 | Curve optimisation tolerance. |
| `-u` | 10 | Output units per bitmap pixel. Drives every coordinate transform below. |

## Coordinate spaces

Four spaces are in play. Mixing them up is the fastest way to a figure that
renders upside down or off-canvas.

1. **Source image pixels** - y down, origin top-left
2. **potrace units** - y **UP**, `POTRACE_U x scale` units per source pixel
3. **SVG viewBox units** - y down
4. **Output units** - viewBox scaled by `unit`

potrace to source pixels, with `k = POTRACE_U x scale` and
`uh = height x k`:

```python
def f(p):
    return (p[0] / k, (uh - p[1]) / k)
```

At the default `TRACE_SCALE=3`, `POTRACE_U=10`, that divisor is
`PT_DIV = 30`.

vvg1 and vvg4 skip the conversion and stay in potrace space, using an SVG
transform instead:

```
transform="translate(0,{uh}) scale(0.1,-0.1)"
```

The negative y scale is what flips potrace's y-up into SVG's y-down.

## Verify with CairoSVG, never ImageMagick

ImageMagick's SVG renderer is not a real SVG renderer:

- It only matches **trivial single-class selectors**. `.m { fill: teal }`
  does not match `class="m quadriceps"`.
- It **silently drops strokes** on large complex paths. The whole teal look
  is built from strokes, so output rendered featureless and solid.
- It applies **non-uniform scaling** if you set `width` without `height`.

This cost three separate debugging rounds where the geometry was correct
and only the preview was lying. Use CairoSVG, or open the file in a
browser:

```python
cairosvg.svg2png(url="out/hybrid-body-front.svg", write_to="p.png",
                 output_width=560, background_color="white")
```

## The empty `<style></style>` is deliberate

CSS beats presentation attributes in the cascade. If the SVG declared:

```html
<style>.m { fill: #5FB3A6 }</style>
```

then `element.setAttribute("fill", "red")` would have **no visible effect,
ever**, because the stylesheet rule keeps winning. Anyone using the file
would conclude the regions are not fillable.

So all styling goes into presentation attributes on each path and the
`<style>` block stays empty. Both approaches then work:

```js
el.setAttribute('fill', 'red');                       // works
// and in a stylesheet:  #chest-left { fill: red }    // also works
```

That is the difference between "labelled" and genuinely "fillable".

## Never `binary_fill_holes` a whole figure

The gap between the legs is an **enclosed region** - bounded by the legs on
both sides, the crotch above, and the image edge below only if the feet are
apart. On a standing figure with arms out, `binary_fill_holes` treats it as
interior and fills it solid. The back view came out with a dark brown wedge
between the legs.

Fix: fill by hole area, skipping any hole that touches the border.

```python
holes = ~mask
lab, n = ndimage.label(holes)
# skip border-touching labels, fill only holes < AT_HOLE_PX
```

`AT_HOLE_PX = 1500` closes genuine speckle while leaving the leg gap open.

## 4-connectivity for segmentation

`vvg2_segment.py` labels with:

```python
CONN4 = np.array([[0, 1, 0], [1, 1, 1], [0, 1, 0]])
```

With the default 8-connectivity, two muscles touching only at a diagonal
pixel merge into one component. Adjacent muscles in this art touch
diagonally at their tips all the time, so 8-connectivity silently loses
regions.

`binary_opening` with a 3x3 kernel runs first for the same reason: it
severs one-pixel bridges that would otherwise fuse neighbours.

## 1px dilation before tracing each region

Regions are traced from their own mask, so two adjacent regions produce two
outlines that meet exactly - and antialiasing puts a visible white hairline
between them. Dilating each mask by 1px makes neighbours overlap slightly,
which hides the seam. The same trick keeps the autotrace tone layers
seamless.

## Two-pass draw for the teal rim

The reference style is a teal body with a dark rim and white gaps between
muscles. It is done with two passes of the **identical path**:

```html
<path class="edge" fill="#1E5B53" stroke="#1E5B53" stroke-width="18.4"/>
<path class="m"    fill="#5FB3A6" stroke="#5FB3A6" stroke-width="8"/>
```

Stroking a filled path **with its own fill colour** fattens the shape
outward by half the stroke width. So the wider dark pass underneath peeks
out as a rim of uniform thickness `(G+S - G)/2 = S/2`, and the leftover
space between muscles reads as white.

`stroke-linejoin="round"` is required - without it, sharp corners throw
long miter spikes.

`GAP_SPREAD` and `RIM` are in **absolute output units**, not relative, so
the line weight is identical across front and back even though the two
views have different source dimensions.

## Body outline underlay

A white-filled, dark-stroked silhouette sits beneath everything. Without it
the figure reads as a scatter of disconnected strips instead of one body,
because the white gaps between muscles have nothing behind them.

## Height normalisation

The front and back source images differ slightly in body height. Both get
normalised so crown-to-sole is the same in output units:

```python
unit = (TARGET_BODY_PX * UNIT) / (lm["sole"] - lm["crown"])
```

Without this the two figures on the combined sheet are noticeably different
heights.

## Landmark reference values

Regression baselines. If a refactor changes these, something broke.

| Figure | crown | neck | shoulder | hand | crotch | ankle | sole |
|---|---|---|---|---|---|---|---|
| ART front | 20 | 196 | 251 | 728 | 827 | 1355 | 1473 |
| ART back | 19 | 192 | 251 | 729 | 828 | 1364 | 1473 |
| TEAL front | 47 | 115 | 136 | 325 | 358 | 525 | 584 |
| TEAL back | 43 | 94 | 113 | 267 | 294 | 446 | 477 |

## Armpit and knee are detected but unused

`vvg_landmarks.analyze` returns them, but `vvg_warp.ANCHORS` leaves them
out. Both are unreliable - the armpit heuristic fires on the first row with
3+ runs, which can be a stray pixel, and the knee is a shallow minimum that
wanders. Including them put visible kinks in the thigh and upper arm.

## The warp grid must be smoothed

Run boundaries jump by a pixel from row to row, so the raw displacement
grid is jittery and warped outlines come out wobbly. The grid is built
subsampled at `step=3`, gaussian-smoothed at `sigma=2.0`, then bilinearly
resampled on lookup.

The vertical grid is smoothed only along y (`sigma=(2.0, 0)`), because
smoothing it across x would shear the figure.

## scipy 1.18 removed `ndarray.ptp()`

Use `arr.max() - arr.min()`.

## Which output to actually use

`hybrid` over `warped`. The warp matches the reference proportions but
visibly distorts the muscle drawing, especially across the shoulders and
thighs - it is stretching art drawn for one body onto another. The hybrid
keeps the original geometry and takes only the palette and the head, which
looks better and is anatomically more honest.
