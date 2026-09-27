# Submitting

1. **Format.** Plain text `.thr`: one `theta rho` pair per line, `#` comments
   allowed. Theta in radians, continuous. 0 ≤ rho ≤ 0.97. One continuous line.
2. **Header.** First comment lines: a title, a handle (any name you like — no
   real name needed), and a line or two of intent. Optionally a line
   `# geometry: true` or `# geometry: machine` (sandlib writes it) and, for a
   design with an up, `# up: top of preview` — the curator rotates to the room.
3. **Check it.** `python3 tools/thr_check.py your-file.thr` — fix any FAULT.
   Notes are advice, not rejections (a deliberate closed loop is fine).
   Preview it honestly: `python3 tools/honest_proof.py your-file.thr`.
4. **Submit.** Open a pull request adding `submissions/<your-handle>/<title>.thr`
   (and the `-honest.png` preview if you like). Up to five files per visit.
   No pull request? Open an issue and attach the file.

Titles must be unique across `submissions/`. The curator may decline, hold, or
draw any submission, and may post a photograph of the result.
