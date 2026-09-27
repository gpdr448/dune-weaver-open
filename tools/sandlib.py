"""
sandlib.py -- a small starting library for drawing one continuous line.

Author in the preview frame: x right, y up, unit disc, angles in degrees
anticlockwise from the right edge. The Builder keeps theta continuous, samples
finely, and writes a .thr.

Two geometries (see MACHINE.md):
    Builder()                 # machine coordinates: what you write is what is
                              # commanded; the table adds its outward offset
                              # (the eye, bowed chords) -- often lovely
    Builder(true_geometry=True)
                              # you author TRUE positions (1.0 = 155 mm from
                              # the real centre); the library compensates so
                              # straight comes out straight. Points inside
                              # r ~0.123 (19 mm) are unreachable and are pushed
                              # out to that circle.

    from sandlib import Builder
    b = Builder()
    b.move(0.9, 0)                 # start at the rim
    b.spiral_to(0.3, turns=3)      # spiral inward three turns
    b.circle(0.2, 0.2, 0.06)       # a ring (a 'boss' at this size)
    b.line(-0.5, -0.4)             # straight pull (in the chosen geometry)
    b.spiral_in_tail()             # park near the centre
    b.write("my-work.thr", "my-work", "handle", "one line of intent")
"""
import math

TAU = 2 * math.pi
RIM = 0.97
STEP = 0.004            # sampling, rho units (~0.6 mm)
C = 0.14                # rho offset of this table (MACHINE.md)


class Builder:
    def __init__(self, true_geometry=False):
        self.true = true_geometry
        self.pts = []           # (theta, rho), commanded

    # ---- core -----------------------------------------------------------
    def _cmd(self, x, y):
        """preview-frame point -> (theta, rho) command."""
        r = math.hypot(x, y)
        if self.true:
            r = max(r * (1 + C) - C, 0.0)
        r = min(r, RIM)
        return math.atan2(y, -x), r

    def _push(self, x, y):
        th, r = self._cmd(x, y)
        if self.pts:
            th0 = self.pts[-1][0]
            th += TAU * round((th0 - th) / TAU)       # keep theta continuous
        self.pts.append((th, r))
        self._xy = (x, y)

    def pos(self):
        return self._xy

    # ---- primitives (all continue from the current point) ----------------
    def move(self, x, y):
        """first point, or a straight pull to (x, y)."""
        if not self.pts:
            self._push(x, y)
        else:
            self.line(x, y)

    def line(self, x, y):
        x0, y0 = self._xy
        n = max(1, math.ceil(math.hypot(x - x0, y - y0) / STEP))
        for i in range(1, n + 1):
            t = i / n
            self._push(x0 + (x - x0) * t, y0 + (y - y0) * t)

    def polyline(self, pts):
        for p in pts:
            self.line(*p)

    def curve(self, fn, n=400):
        """fn(t) -> (x, y) for t in [0, 1]; pulls to fn(0) first."""
        self.line(*fn(0.0))
        for i in range(1, n + 1):
            self._push(*fn(i / n))

    def arc(self, cx, cy, r, a0, a1):
        """arc about (cx, cy) from angle a0 to a1 (degrees; a1 > a0 anticlockwise)."""
        n = max(8, math.ceil(abs(math.radians(a1 - a0)) * r / STEP))
        self.curve(lambda t: (cx + r * math.cos(math.radians(a0 + (a1 - a0) * t)),
                              cy + r * math.sin(math.radians(a0 + (a1 - a0) * t))), n)

    def circle(self, cx, cy, r, start=270, ccw=True):
        """one full circle entered and left at angle `start` (270 = its foot)."""
        self.arc(cx, cy, r, start, start + (360 if ccw else -360))

    def spiral_to(self, r1, turns, ccw=True):
        """Archimedean spiral about the centre from the current point to radius r1."""
        x0, y0 = self._xy
        r0 = math.hypot(x0, y0); a0 = math.degrees(math.atan2(y0, x0))
        s = 1 if ccw else -1
        n = max(20, math.ceil(turns * TAU * max(r0, r1) / STEP))
        for i in range(1, n + 1):
            t = i / n
            a = math.radians(a0 + s * 360 * turns * t); r = r0 + (r1 - r0) * t
            self._push(r * math.cos(a), r * math.sin(a))

    def ring_about_centre(self, r, degrees, ccw=True):
        """constant-radius arc about the table centre from the current angle."""
        x0, y0 = self._xy
        a0 = math.degrees(math.atan2(y0, x0))
        self.arc(0, 0, r, a0, a0 + (degrees if ccw else -degrees))

    def spiral_in_tail(self, turns=2, r_end=0.13):
        self.spiral_to(r_end, turns)

    # ---- output ----------------------------------------------------------
    def write(self, path, title, handle, intent):
        # resample: long commanded steps become visible spirals on the machine
        out = [self.pts[0]]
        for (t0, r0), (t1, r1) in zip(self.pts, self.pts[1:]):
            arc = math.hypot(r1 - r0, (r0 + r1) / 2 * (t1 - t0))
            n = max(1, math.ceil(arc / 0.005))
            for i in range(1, n + 1):
                f = i / n
                out.append((t0 + (t1 - t0) * f, r0 + (r1 - r0) * f))
        with open(path, "w") as fh:
            fh.write(f"# {title}\n# {handle}\n# {intent}\n")
            fh.write(f"# geometry: {'true (compensated)' if self.true else 'machine'}\n")
            for t, r in out:
                fh.write(f"{t:.6f} {r:.5f}\n")
        return out
