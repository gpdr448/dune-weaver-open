"""
sandsim.py — a sand-aware proof renderer for the Ombonad table.

The hairline proof draws the path. This draws what the path does to the
medium: a 10mm ball dragged along the floor of a thin baking-soda layer,
sand shoved out of its footprint into side-berms and a bow wave, the pile
relaxing to its angle of repose, then the height field lit two ways
(overhead and raking) with the tray floor showing through where the sand
is scraped thin.

v1 (2026-09-26): constants fitted to the round-1 bench photographs. The
geometry now knows that this table's rho 0 is a circle ~19 mm out, not the
centre (true radius = k*(rho + c)); the soda is cohesive enough that a 6 mm
knife ridge survives; the tray floor is pale, so no dark lines. All constants
live in PARAMS; a ruler or a new round of photos changes numbers, not code.

What it still gets wrong (round 1): the hub mound (the real one is a raised
pile, the sim leaves the unswept disc flat), the lumpy pile at the rim, and
the fine "zipper" teeth where a line crosses the clear's grain.

usage:
    python3 sandsim.py pattern.thr [more.thr ...]   -> pattern-sim.png beside each
    options: --no-clear   start from a flat field instead of the default clear
             --light AZ   raking-light azimuth in degrees, preview frame
                          (0 = from the right, 90 = from the top)
"""
import math, sys, os
import numpy as np
from PIL import Image

PARAMS = dict(
    k_mm=136.0,         # radial scale: 1.0 of rho = 136 mm of travel   (round-1 photos)
    offset_c=0.14,      # rho 0 sits 0.14*k = 19 mm off centre           (round-1 photos)
    field_mm=155.0,     # true radius at rho 1.0 = k*(1+c)
    ball_r=5.0,         # 10mm ball
    depth=1.8,          # effective soda depth in the field, mm (fit to the round-1 ladder)
    cell=0.5,           # grid resolution, mm
    repose_deg=55.0,    # soda is cohesive: knife ridges survive at 6 mm (round-1)
    side_bias=1.0,      # weight of lateral deposit (berms)
    fwd_bias=0.30,      # weight of forward deposit (bow wave)
    ring_w=1.5,         # width of the deposit ring outside the footprint, mm
    relax_iters=4,
    floor_rgb=(228, 222, 208),  # the tray floor is pale: no dark lines in round-1 photos
    sand_rgb=(238, 234, 226),   # soda
    thin_mm=0.35,       # below this the floor starts to show
)

TAU = 2 * math.pi


# --------------------------------------------------------------------------
# path handling
# --------------------------------------------------------------------------
def read_thr(path):
    pts = []
    with open(path) as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            a = line.split()
            pts.append((float(a[0]), float(a[1])))
    return pts


def densify(pts, step_mm, R, c=None):
    """The controller interpolates linearly in (theta, rho) between points,
    so a long step is a spiral, not a chord. Reproduce that, then return
    xy in mm (app frame: x = r*cos, y = r*sin) with the TRUE radius
    r = k*(rho + c): this table's rho 0 is not the centre (round-1 finding)."""
    if c is None: c = PARAMS["offset_c"]
    out = []
    for (t0, r0), (t1, r1) in zip(pts, pts[1:]):
        arc = math.hypot((r1 - r0) * R, 0.5 * (r0 + r1) * R * (t1 - t0))
        n = max(1, int(math.ceil(arc / step_mm)))
        for i in range(n):
            f = i / n
            t = t0 + (t1 - t0) * f
            r = r0 + (r1 - r0) * f
            out.append((t, r))
    out.append(pts[-1])
    a = np.array(out)
    r = (np.maximum(a[:, 1], 0.0) + c) * R
    return np.stack([r * np.cos(a[:, 0]), r * np.sin(a[:, 0])], axis=1)


# --------------------------------------------------------------------------
# the medium
# --------------------------------------------------------------------------
class Field:
    def __init__(self, p=PARAMS, seed=7):
        self.p = p
        self.c = p["cell"]
        self.half = p["field_mm"] + 12.0
        self.n = int(round(2 * self.half / self.c))
        rng = np.random.default_rng(seed)
        self.h = np.full((self.n, self.n), p["depth"], dtype=np.float64)
        self.h += rng.normal(0, 0.02, self.h.shape)
        R = p["ball_r"]
        k = int(math.ceil((R + p["ring_w"] + 5.0) / self.c))
        self.k = k
        o = np.arange(-k, k + 1) * self.c
        self.ox, self.oy = np.meshgrid(o, o)  # patch offsets (x across cols, y across rows)
        self.slope = math.tan(math.radians(p["repose_deg"])) * self.c

    def idx(self, x, y):
        return (int(round((y + self.half) / self.c)), int(round((x + self.half) / self.c)))

    def step(self, x, y, ux, uy):
        p = self.p
        R = p["ball_r"]
        i, j = self.idx(x, y)
        k = self.k
        sl = (slice(i - k, i + k + 1), slice(j - k, j + k + 1))
        H = self.h[sl]
        # exact sub-cell ball position
        cx = (j * self.c - self.half)
        cy = (i * self.c - self.half)
        dx = self.ox - (x - cx)
        dy = self.oy - (y - cy)
        d = np.hypot(dx, dy)
        inside = d < R
        zb = np.where(inside, R - np.sqrt(np.clip(R * R - d * d, 0, None)), np.inf)
        for _ in range(2):
            ex = np.clip(H - zb, 0, None)
            E = ex.sum()
            if E <= 1e-9:
                break
            H -= ex
            # deposit ring
            ring = (d >= R) & (d < R + p["ring_w"])
            cosphi = (dx * ux + dy * uy) / np.maximum(d, 1e-9)
            sinphi = np.sqrt(np.clip(1 - cosphi ** 2, 0, None))
            w = np.where(ring & (cosphi > -0.2),
                         p["side_bias"] * sinphi + p["fwd_bias"] * np.clip(cosphi, 0, None), 0.0)
            ws = w.sum()
            if ws <= 0:
                w = ring.astype(float); ws = w.sum()
            H += E * w / ws
            self._relax(H, zb)
        self.h[sl] = H

    def _relax(self, H, zb):
        s = self.slope
        for _ in range(self.p["relax_iters"]):
            # flux along x
            dh = H[:, :-1] - H[:, 1:]
            q = 0.25 * np.clip(np.abs(dh) - s, 0, None) * np.sign(dh)
            H[:, :-1] -= q
            H[:, 1:] += q
            dh = H[:-1, :] - H[1:, :]
            q = 0.25 * np.clip(np.abs(dh) - s, 0, None) * np.sign(dh)
            H[:-1, :] -= q
            H[1:, :] += q
        # sand that slid under the ball gets pushed back out next pass of the loop
        np.clip(H, 0, None, out=H)

    def run(self, xy, step_mm=None):
        step_mm = step_mm or self.c
        # resample xy to uniform spacing ~ step_mm
        seg = np.hypot(*np.diff(xy, axis=0).T)
        s = np.concatenate([[0], np.cumsum(seg)])
        if s[-1] <= 0:
            return
        ss = np.arange(0, s[-1], step_mm)
        X = np.interp(ss, s, xy[:, 0]); Y = np.interp(ss, s, xy[:, 1])
        ux_prev, uy_prev = 1.0, 0.0
        for m in range(len(ss)):
            if m + 1 < len(ss):
                ux, uy = X[m + 1] - X[m], Y[m + 1] - Y[m]
                L = math.hypot(ux, uy)
                if L > 1e-9:
                    ux, uy = ux / L, uy / L
                    ux_prev, uy_prev = ux, uy
                else:
                    ux, uy = ux_prev, uy_prev
            else:
                ux, uy = ux_prev, uy_prev
            self.step(X[m], Y[m], ux, uy)

    def settle(self, iters=6):
        s = self.slope
        H = self.h
        for _ in range(iters):
            dh = H[:, :-1] - H[:, 1:]
            q = 0.25 * np.clip(np.abs(dh) - s, 0, None) * np.sign(dh)
            H[:, :-1] -= q; H[:, 1:] += q
            dh = H[:-1, :] - H[1:, :]
            q = 0.25 * np.clip(np.abs(dh) - s, 0, None) * np.sign(dh)
            H[:-1, :] -= q; H[1:, :] += q


# --------------------------------------------------------------------------
# light
# --------------------------------------------------------------------------
def render(field, light_az_deg=0.0, light_el_deg=14.0, size=720, mode="raking"):
    """Render in the app preview frame (x flipped, y up) so sim and hairline
    proofs overlay. light_az: direction the light COMES FROM, preview frame,
    0 = from the right edge of the picture, 90 = from the top."""
    p = field.p
    H = field.h
    c = field.c
    gy, gx = np.gradient(H, c)           # rows = +y (math), cols = +x (math)
    # convert to preview frame: px = -x, py(up) = +y
    nx, ny = gx, -gy                     # careful: build normal in math frame first
    N = np.stack([-gx, -gy, np.ones_like(H)], axis=-1)
    N /= np.linalg.norm(N, axis=-1, keepdims=True)
    # light direction in math frame: preview-right is math -x
    az = math.radians(light_az_deg)
    el = math.radians(light_el_deg if mode == "raking" else 65.0)
    Lx, Ly, Lz = -math.cos(az) * math.cos(el), math.sin(az) * math.cos(el), math.sin(el)
    lam = np.clip(N[..., 0] * Lx + N[..., 1] * Ly + N[..., 2] * Lz, 0, None)
    # cast shadows: march toward the light
    shadow = np.zeros_like(H, dtype=bool)
    if mode == "raking":
        dirx, diry = Lx / math.cos(el), Ly / math.cos(el)
        tan_el = math.tan(el)
        P = np.pad(H, 40, mode="edge")      # no wrap-around at the image edge
        n = H.shape[0]
        for kk in range(1, 40):
            sx = int(round(dirx * kk)); sy = int(round(diry * kk))
            sh = P[40 + sy:40 + sy + n, 40 + sx:40 + sx + n]
            shadow |= (sh - H) > kk * c * tan_el
    flat = math.sin(el)
    if mode == "raking":
        shade = 0.22 + 0.62 * lam / max(flat, 1e-3)
        shade = np.where(shadow, 0.22, shade)
    else:
        shade = 0.55 + 0.45 * lam / flat
    shade = np.clip(shade, 0, 1.25)
    thin = np.clip(H / p["thin_mm"], 0, 1)[..., None]
    sand = np.array(p["sand_rgb"], float); floor = np.array(p["floor_rgb"], float)
    alb = floor + (sand - floor) * thin
    img = np.clip(alb * shade[..., None], 0, 255).astype(np.uint8)
    # mask outside the tray view (field + margin), then to preview frame
    n = field.n
    yy, xx = np.mgrid[0:n, 0:n]
    rr = np.hypot((xx - n / 2) * c, (yy - n / 2) * c)
    img[rr > p["field_mm"] + 8] = (43, 36, 30)
    img = img[::-1, ::-1]   # rows: math y up -> image down ; cols: preview x = -math x
    im = Image.fromarray(img)
    return im.resize((size, size), Image.LANCZOS)


# --------------------------------------------------------------------------
def clear_spiral(from_in=True, turns_rad=205.682, n=3448):
    """the app's default clears, regenerated: an Archimedean spiral of ~32.7
    turns (pitch 0.0306 rho). clear_from_in runs centre -> rim with theta
    falling; clear_from_out is its mirror, rim -> centre."""
    pts = [(-turns_rad * i / n, i / n) for i in range(n + 1)]
    if from_in:
        return pts
    return [(turns_rad * i / n, 1 - i / n) for i in range(n + 1)]


def simulate(pts, clear=True, p=PARAMS, verbose=False):
    f = Field(p)
    if clear:
        # the app's adaptive clear: pattern starting at rho >= 0.5 -> clear_from_in
        cp = clear_spiral(from_in=pts[0][1] >= 0.5)
        # the app moves from the clear's end to the pattern's start
        # (start theta normalised mod 2pi, nearest branch)
        t_end = cp[-1][0]
        t0 = pts[0][0]
        kk = round((t_end - t0) / TAU)
        shifted = [(t + TAU * kk, r) for t, r in pts]
        full = cp + shifted
    else:
        full = pts
    xy = densify(full, 0.5, p["k_mm"], p["offset_c"])
    if verbose:
        print(f"  path {np.hypot(*np.diff(xy, axis=0).T).sum()/1000:.1f} m")
    f.run(xy)
    f.settle()
    return f


def contact(pts, f, light_az=0.0, size=720):
    """three panels: honest hairline proof | overhead | raking.
    The hairline is drawn where the table really puts it (rho -> rho + c)."""
    from PIL import ImageDraw
    p = f.p
    hp = Image.new("RGB", (size, size), (43, 36, 30))
    dr = ImageDraw.Draw(hp)
    C = size / 2
    S = size / 2 / ((p["field_mm"] + 12) / p["k_mm"])      # px per unit of k
    c = p["offset_c"]
    dr.ellipse([C - S * (1 + c), C - S * (1 + c), C + S * (1 + c), C + S * (1 + c)], outline=(110, 98, 84))
    dr.ellipse([C - S * c, C - S * c, C + S * c, C + S * c], outline=(80, 70, 60))
    poly = [(C - (r + c) * S * math.cos(t), C - (r + c) * S * math.sin(t)) for t, r in pts]
    dr.line(poly, fill=(232, 219, 190), width=1)
    a = render(f, mode="overhead", size=size)
    b = render(f, light_az_deg=light_az, mode="raking", size=size)
    out = Image.new("RGB", (size * 3 + 20, size), (30, 26, 22))
    out.paste(hp, (0, 0)); out.paste(a, (size + 10, 0)); out.paste(b, (2 * size + 20, 0))
    return out


if __name__ == "__main__":
    args = sys.argv[1:]
    clear = "--no-clear" not in args
    az = 0.0
    if "--light" in args:
        az = float(args[args.index("--light") + 1])
    files = [a for a in args if a.endswith(".thr")]
    for fn in files:
        pts = read_thr(fn)
        f = simulate(pts, clear=clear, verbose=True)
        out = contact(pts, f, light_az=az)
        dst = fn[:-4] + "-sim.png"
        out.save(dst)
        print("wrote", dst)
