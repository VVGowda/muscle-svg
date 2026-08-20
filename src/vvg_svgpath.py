"""vvg_svgpath - absolute-cubic SVG path parser and emitter.

Everything downstream (warping, scaling, head placement) works as
emit(parse(d), transform_fn). Normalising every command to absolute cubics
up front means a transform only ever has to handle one point at a time.
"""
import re

NUM = re.compile(r'[-+]?(?:\d*\.\d+|\d+)(?:[eE][-+]?\d+)?')
CMD = re.compile(r'([MmLlHhVvCcSsQqTtZz])')


def parse(d):
    """-> list of subpaths; each = (start_pt, [(c1, c2, p), ...]) as absolute cubics."""
    toks = [t for t in CMD.split(d) if t.strip()]
    subs, cur, start, pt, prev_c2, cmd = [], None, None, (0.0, 0.0), None, None
    i = 0
    while i < len(toks):
        t = toks[i]
        if CMD.fullmatch(t):
            cmd = t; i += 1
            nums = []
            if i < len(toks) and not CMD.fullmatch(toks[i]):
                nums = [float(x) for x in NUM.findall(toks[i])]; i += 1
        else:
            nums = [float(x) for x in NUM.findall(t)]; i += 1
        rel = cmd.islower(); K = cmd.upper()
        def A(x, y): return (pt[0] + x, pt[1] + y) if rel else (x, y)
        if K == 'M':
            for k in range(0, len(nums), 2):
                p = A(nums[k], nums[k + 1])
                if k == 0:
                    if cur: subs.append((start, cur))
                    cur, start = [], p
                else:
                    cur.append((p, p, p))
                pt = p
            prev_c2 = None
        elif K in 'LHV':
            step = {'L': 2, 'H': 1, 'V': 1}[K]
            for k in range(0, len(nums), step):
                if K == 'L': p = A(nums[k], nums[k + 1])
                elif K == 'H': p = (pt[0] + nums[k], pt[1]) if rel else (nums[k], pt[1])
                else: p = (pt[0], pt[1] + nums[k]) if rel else (pt[0], nums[k])
                cur.append((pt, p, p)); pt = p
            prev_c2 = None
        elif K == 'C':
            for k in range(0, len(nums), 6):
                c1 = A(nums[k], nums[k + 1]); c2 = A(nums[k + 2], nums[k + 3]); p = A(nums[k + 4], nums[k + 5])
                cur.append((c1, c2, p)); prev_c2 = c2; pt = p
        elif K == 'S':
            for k in range(0, len(nums), 4):
                c1 = (2 * pt[0] - prev_c2[0], 2 * pt[1] - prev_c2[1]) if prev_c2 else pt
                c2 = A(nums[k], nums[k + 1]); p = A(nums[k + 2], nums[k + 3])
                cur.append((c1, c2, p)); prev_c2 = c2; pt = p
        elif K == 'Z':
            if cur is not None:
                subs.append((start, cur)); pt = start; cur = []
            prev_c2 = None
    if cur: subs.append((start, cur))
    return [(s, segs) for s, segs in subs if segs]


def emit(subs, f=lambda p: p, nd=1):
    def n(v):
        s = ('%.*f' % (nd, v)).rstrip('0').rstrip('.')
        return s if s not in ('', '-0') else '0'
    out = []
    for start, segs in subs:
        p = f(start)
        out.append('M%s %s' % (n(p[0]), n(p[1])))
        for c1, c2, q in segs:
            a, b, c = f(c1), f(c2), f(q)
            out.append('C%s %s %s %s %s %s' % (n(a[0]), n(a[1]), n(b[0]), n(b[1]), n(c[0]), n(c[1])))
        out.append('Z')
    return ''.join(out)
