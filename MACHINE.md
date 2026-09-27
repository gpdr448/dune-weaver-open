# The machine

A polar ("theta-rho") sand table of the Dune Weaver family.

| | |
|---|---|
| Drawing field | a disc ≈ 310 mm across (ball centre reaches ≈155 mm from the axis) |
| Scribe | 10 mm chrome-steel ball, dragged by a magnet under the floor |
| Medium | baking soda, ≈2 mm deep; the tray floor is pale, so lines read by relief, not colour |
| Line | the ball plows a trough ≈9–10 mm wide with a berm on each side |
| Motion | one continuous line; the ball cannot lift |
| Before every drawing | the app runs a spiral clear (≈32 turns) that leaves fine concentric ridges — the **grain** |

## Coordinates, and the one thing previews get wrong

Files give `theta rho` pairs: theta in radians (continuous — revolutions
accumulate), rho from 0 to 1. The machine moves linearly in (theta, rho)
between points, so a long step is a spiral arc, not a straight chord: sample
finely (≈0.005 rho of arc).

**Rho 0 is not the centre on this table.** The true radius of the ball is

```
radius ≈ 136 mm × (rho + 0.14)        rho 0 → ≈19 mm,  rho 1 → ≈155 mm
```

Theta is accurate. Consequences:

- Nothing reaches the true centre. A ≈40 mm mound of unswept sand sits there
  after every clear. A line "through the centre" actually rides a semicircle of
  radius ≈19 mm around it.
- Straight lines bow outward, away from the centre — most for lines passing
  near it. Every full-field set of parallel lines gets a lens-shaped **eye** at
  the centre. Many find it beautiful; design with it or compensate it away.
- Shapes near the centre are stretched sideways by (rho + 0.14)/rho — a circle
  at rho 0.3 comes out ≈1.5× as wide as it is deep.
- Sideways spacing at radius rho is (rho + 0.14)·Δθ, not rho·Δθ.

`tools/honest_proof.py` draws your file both ways. Its `compensate(x, y)` gives
commands for true geometry if you want straight to mean straight
(`rho_cmd = 1.14·rho_true − 0.14`, where rho_true = true radius / 155 mm).

## Before your first point: the clear and the lead-in

The app picks the clear from your first point: start at rho ≥ 0.5 and it runs
**centre → rim** (ending at rho ≈1, preview angle ≈85°, just right of the top);
start below 0.5 and it runs **rim → centre** (ending at rho 0, angle ≈275°). It
then travels straight to your first point, interpolating theta between the two
angles — which can plough a long stray arc along the rim. Start near where the
clear ends, or make the lead-in part of the design. `thr_check.py` reports the
sweep.

## Limits and sizes

- Keep rho ≤ 0.97. Features beyond ≈0.90 blur into a plowed band along the rim.
- rho below 0 is invalid. rho 0 is fine (it is the 19 mm circle).
- **Path length**: most good works are 3–15 m of path (1–5 minutes of drawing
  at ≈3 m/min, after a ≈6-minute clear). Up to ≈60 m (≈20 min) is possible;
  more is rarely better.
- **Line width**: a single pass ≈9–10 mm; a pass retraced at offset 0.012
  ≈11 mm; at 0.025 ≈13 mm; at 0.040 a seam starts to show.
- **Smallest legible marks**: a ring needs r ≥ 0.05 (below that it is a
  dimple or a cup); strokes of a glyph need ≥ 0.075 between them, so a letter
  or sign wants ≈0.25–0.35 rho of height (35–50 mm). The whole radius is only
  ≈15 line-widths.

## Light

The table is seen in changing daylight. Overhead light shows density and
shadowed troughs; low light shows only ridges that run *across* it — ridges
parallel to the light go flat. So the clear's rings vanish in a band pointing
at the light, and a design reads differently morning and evening. (The
low-light panel of `sandsim.py` shows this band; it is real, not a bug.)
