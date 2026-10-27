#!/usr/bin/env python3
"""Fit a JamesDSP GraphicEQ curve with peaking biquads for a speaker-dsp profile.

usage: scripts/fit-graphiceq.py "480 0; 600 -5; 700 -16; ..." [--bands N] [--lo HZ] [--hi HZ]

Prints `Filter N: ON PK Fc <hz> Hz Gain <db> dB Q <q>` lines (the REW/AutoEQ export format the
profiles use) and the fit error on stderr. Between points the target is log-linear in frequency,
flat beyond the ends; JamesDSP's own interpolation may differ by a fraction of a dB. A curve that
never rises above 0 dB gets cut-only bands: boosts cancelling deeper cuts fit as well on paper but
add gain wherever they drift apart.
"""
import argparse
import math
import random
import sys

RATE = 48000


def parse_points(text):
    text = text.split(":", 1)[1] if text.lower().startswith("graphiceq") else text
    pts = []
    for pair in text.split(";"):
        if pair.strip():
            f, g = pair.split()
            pts.append((float(f), float(g)))
    return sorted(pts)


def target(pts, f):
    if f <= pts[0][0]:
        return pts[0][1]
    for (f0, g0), (f1, g1) in zip(pts, pts[1:]):
        if f <= f1:
            t = math.log(f / f0) / math.log(f1 / f0)
            return g0 + t * (g1 - g0)
    return pts[-1][1]


def peaking_db(fc, gain, q, cos_w):
    # RBJ peaking biquad: the same coefficients PipeWire's bq_peaking uses.
    a = 10 ** (gain / 40)
    w0 = 2 * math.pi * fc / RATE
    alpha = math.sin(w0) / (2 * q)
    c = -2 * math.cos(w0)
    b0, b2 = 1 + alpha * a, 1 - alpha * a
    a0, a2 = 1 + alpha / a, 1 - alpha / a
    nb0, nb1 = b0 * b0 + c * c + b2 * b2, 2 * c * (b0 + b2)
    na0, na1 = a0 * a0 + c * c + a2 * a2, 2 * c * (a0 + a2)
    out = []
    for cw, c2w in cos_w:
        num = nb0 + nb1 * cw + 2 * b0 * b2 * c2w
        den = na0 + na1 * cw + 2 * a0 * a2 * c2w
        out.append(10 * math.log10(num / den))
    return out


# x holds log(Hz), gain, log(Q) per band. Cut-only bands store gain as log(-dB): smooth all the
# way to 0 dB, where a clamped dB value would pin the optimiser to the wall and waste the band.
def unpack(x, cut_only):
    gain = (lambda u: -math.exp(u)) if cut_only else (lambda g: g)
    return [(math.exp(x[i]), gain(x[i + 1]), math.exp(x[i + 2])) for i in range(0, len(x), 3)]


def clamp(x, lo, hi, cut_only):
    glo, ghi = (math.log(0.05), math.log(30.0)) if cut_only else (-30.0, 12.0)
    out = list(x)
    for i in range(0, len(out), 3):
        out[i] = min(max(out[i], math.log(lo)), math.log(hi))
        out[i + 1] = min(max(out[i + 1], glo), ghi)
        out[i + 2] = min(max(out[i + 2], math.log(0.3)), math.log(8.0))
    return out


def response(x, cos_w, cut_only):
    model = [0.0] * len(cos_w)
    for fc, g, q in unpack(x, cut_only):
        for i, v in enumerate(peaking_db(fc, g, q, cos_w)):
            model[i] += v
    return model


def make_cost(cos_w, want, weight, lo, hi, cut_only):
    def cost(x):
        model = response(clamp(x, lo, hi, cut_only), cos_w, cut_only)
        return sum(k * (m - w) ** 2 for m, w, k in zip(model, want, weight))
    return cost


def nelder_mead(f, x0, step, iters):
    n = len(x0)
    pts = [list(x0)] + [[x0[j] + (step[j] if j == i else 0.0) for j in range(n)] for i in range(n)]
    vals = [f(p) for p in pts]
    for _ in range(iters):
        order = sorted(range(n + 1), key=vals.__getitem__)
        pts, vals = [pts[i] for i in order], [vals[i] for i in order]
        cen = [sum(p[j] for p in pts[:-1]) / n for j in range(n)]
        ref = [cen[j] + (cen[j] - pts[-1][j]) for j in range(n)]
        fr = f(ref)
        if fr < vals[0]:
            exp = [cen[j] + 2 * (cen[j] - pts[-1][j]) for j in range(n)]
            fe = f(exp)
            pts[-1], vals[-1] = (exp, fe) if fe < fr else (ref, fr)
        elif fr < vals[-2]:
            pts[-1], vals[-1] = ref, fr
        else:
            con = [cen[j] + 0.5 * (pts[-1][j] - cen[j]) for j in range(n)]
            fcon = f(con)
            if fcon < vals[-1]:
                pts[-1], vals[-1] = con, fcon
            else:
                for i in range(1, n + 1):
                    pts[i] = [pts[0][j] + 0.5 * (pts[i][j] - pts[0][j]) for j in range(n)]
                    vals[i] = f(pts[i])
    best = min(range(n + 1), key=vals.__getitem__)
    return pts[best], vals[best]


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("curve", help='GraphicEQ points, "Hz dB; Hz dB; ..."')
    ap.add_argument("--bands", type=int, default=8)
    ap.add_argument("--lo", type=float, default=300.0, help="speaker band low edge (Hz)")
    ap.add_argument("--hi", type=float, default=12000.0, help="speaker band high edge (Hz)")
    args = ap.parse_args()

    pts = parse_points(args.curve)
    cut_only = max(g for _, g in pts) <= 0
    # 100 Hz-20 kHz at 1/24 octave; outside the speaker band errors count a tenth, enough to stop
    # bands spilling past the curve's ends.
    grid, f = [], 100.0
    while f <= 20000.0:
        grid.append(f)
        f *= 2 ** (1 / 24)
    cos_w = [(math.cos(2 * math.pi * g / RATE), math.cos(4 * math.pi * g / RATE)) for g in grid]
    want = [target(pts, g) for g in grid]
    inband = [i for i, g in enumerate(grid) if args.lo <= g <= args.hi]
    weight = [0.1] * len(grid)
    for i in inband:
        weight[i] = 1.0
    cost = make_cost(cos_w, want, weight, args.lo, args.hi, cut_only)
    # Seeded: the same curve always fits to the same lines, so a refit is a clean diff.
    random.seed(1)

    # Greedy: each new band starts on the largest remaining in-band error, then all bands are refit.
    # Cut-only bands start where the most cut is still missing: a band placed on an over-cut spot
    # pins at 0 dB and is wasted.
    x = []
    for _ in range(args.bands):
        model = response(x, cos_w, cut_only)
        if cut_only:
            k = min(inband, key=lambda i: want[i] - model[i])
        else:
            k = max(inband, key=lambda i: abs(want[i] - model[i]))
        r = want[k] - model[k]
        if abs(r) < 0.3:
            break
        x += [math.log(grid[k]), math.log(max(-r, 0.3)) if cut_only else r, math.log(2.0)]
        best, bestv = x, cost(x)
        for _ in range(2):
            # Initial simplex per band: log Hz, gain (1.5 dB, or a ~4.5x factor on a cut-only
            # log(-dB)), log Q.
            step = [0.15 + 0.1 * random.random(), 1.5, 0.3] * (len(x) // 3)
            cand, v = nelder_mead(cost, best, step, 150 * len(x))
            if v < bestv:
                best, bestv = cand, v
        x = clamp(best, args.lo, args.hi, cut_only)

    bands = sorted(unpack(x, cut_only))
    model = response(x, cos_w, cut_only)
    outband = set(range(len(grid))) - set(inband)
    err = [abs(model[i] - want[i]) for i in inband]
    out = [abs(model[i] - want[i]) for i in sorted(outband)]
    for n, (fc, g, q) in enumerate(bands, 1):
        print(f"Filter {n}: ON PK Fc {fc:.0f} Hz Gain {g:.1f} dB Q {q:.2f}")
    print(f"fit {args.lo:.0f}-{args.hi:.0f} Hz: max error {max(err):.2f} dB, "
          f"rms {math.sqrt(sum(e * e for e in err) / len(err)):.2f} dB; "
          f"outside: max {max(out):.2f} dB", file=sys.stderr)


if __name__ == "__main__":
    main()
