"""
honest_proof.py — the hairline proof, drawn where this table actually puts it.

Round-1 bench photographs (2026-09-26) showed that on this table rho 0 is NOT
the centre of the field. The machine's rho runs linearly from a circle of
radius ~19 mm (rho 0) out to ~155 mm (rho 1):

        true radius  =  K * (rho + C)        K ~ 136 mm,  C ~ 0.14

Theta is honest. So every point of a design is pushed straight outward by
~19 mm and the radial scale is ~12 % tighter than the proof assumes. What
this does to a drawing:

  * straight chords bow outward, away from the hub (most for chords that pass
    near the centre): the "eye" that every vertical raster on this table has;
  * shapes near the hub stretch sideways by (rho + C) / rho: a circle drawn
    at rho .30 comes out ~1.5x as wide as it is deep;
  * anything that "passes through the centre" really rides a semicircle of
    radius ~19 mm around it: this, not a clamp, is the old "dead zone";
  * sideways spacing at radius rho is K*(rho + C)*dtheta, not rho*dtheta.

Usage
    python3 honest_proof.py pattern.thr [more.thr ...]
        -> pattern-honest.png: the naive proof and the honest proof side by side

    from honest_proof import compensate
        compensate(x, y) turns a point in "true" unit-disc coordinates
        (1.0 = 155 mm from the true centre, same frame as the app preview)
        into the (theta, rho) to command, so that geometry comes out true.
        Points closer than ~19 mm to the centre cannot be reached: they
        come back as None.

The two constants live here and in sandsim.PARAMS. If a ruler says otherwise,
change them in both places.
"""
import math, sys
from PIL import Image, ImageDraw

K_MM = 136.0
C = 0.14
FIELD_MM = K_MM * (1 + C)          # ~155 mm at rho 1


def true_xy(theta, rho):
    """(theta, rho) as commanded -> true position in unit-disc coordinates
    (1.0 = FIELD_MM), app-preview frame (x = -r cos t, y = r sin t)."""
    r = (rho + C) / (1 + C)
    return -r * math.cos(theta), r * math.sin(theta)


def compensate(x, y):
    """true unit-disc point (app-preview frame) -> (theta, rho) to command,
    or None if it lies inside the unreachable hub (radius C/(1+C) ~ 0.123)."""
    r = math.hypot(x, y)
    rho = r * (1 + C) - C
    if rho < 0:
        return None
    theta = math.atan2(y, -x)
    return theta, rho


def read_thr(path):
    pts = []
    for line in open(path):
        line = line.strip()
        if line and not line.startswith("#"):
            a = line.split()
            pts.append((float(a[0]), float(a[1])))
    return pts


def draw(pts, size=720, honest=True):
    bg, fg, rim = (43, 36, 30), (232, 219, 190), (110, 98, 84)
    im = Image.new("RGB", (size, size), bg)
    d = ImageDraw.Draw(im)
    Cx = size / 2
    S = size / 2 * 0.94
    d.ellipse([Cx - S, Cx - S, Cx + S, Cx + S], outline=rim)
    if honest:
        h = S * C / (1 + C)
        d.ellipse([Cx - h, Cx - h, Cx + h, Cx + h], outline=(80, 70, 60))
        poly = []
        for t, r in pts:
            x, y = true_xy(t, r)
            poly.append((Cx + S * x, Cx - S * y))
    else:
        poly = [(Cx - r * S * math.cos(t), Cx - r * S * math.sin(t)) for t, r in pts]
    d.line(poly, fill=fg, width=1)
    return im


if __name__ == "__main__":
    for fn in [a for a in sys.argv[1:] if a.endswith(".thr")]:
        pts = read_thr(fn)
        a, b = draw(pts, honest=False), draw(pts, honest=True)
        out = Image.new("RGB", (a.size[0] * 2 + 10, a.size[1]), (20, 20, 20))
        out.paste(a, (0, 0)); out.paste(b, (a.size[0] + 10, 0))
        dst = fn[:-4] + "-honest.png"
        out.save(dst)
        print("wrote", dst)
