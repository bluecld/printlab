"""Slice an STL with PrusaSlicer CLI using a K2 profile, then read the result.

Usage: python -I slice.py <profile.ini> <out.gcode> <a_print.stl> [b_print.stl ...]
Several STLs go on one plate, auto-arranged.
Reports time, grams, metres, and how much extrusion went to supports and bridges.
"""
import os, sys, re, shutil, subprocess, collections

# Linux: prusa-slicer on PATH. Windows: the console build, which prints the CLI messages.
PRUSA = (shutil.which("prusa-slicer") or shutil.which("prusa-slicer-console")
         or os.path.expandvars(r"%ProgramFiles%\Prusa3D\PrusaSlicer\prusa-slicer-console.exe"))


def slice_part(ini, out, stls):
    place = ["--center", "130,130"] + (["--merge"] if len(stls) > 1 else [])  # --merge puts all inputs on one plate
    cmd = [PRUSA, "--export-gcode", "--load", ini, *place, "-o", out, *stls]
    r = subprocess.run(cmd, capture_output=True, encoding="utf-8", errors="replace")
    if r.returncode or "Slicing result exported" not in r.stdout + r.stderr:
        print(r.stdout[-2000:], r.stderr[-2000:])
        raise SystemExit("SLICE FAILED")
    return read(out)


def read(gcode):
    e_by_type = collections.Counter()
    kind, meta = "other", {}
    with open(gcode, encoding="utf-8", errors="replace") as f:
        for line in f:
            if line.startswith(";TYPE:"):
                kind = line[6:].strip()
            elif line.startswith("G1") and " E" in line:
                m = re.search(r" E(-?[\d.]+)", line)
                if m and float(m.group(1)) > 0:
                    e_by_type[kind] += float(m.group(1))
            elif line.startswith("; ") and " = " in line:
                k, v = line[2:].split(" = ", 1)
                meta[k.strip()] = v.strip()
    total = sum(e_by_type.values()) or 1
    share = lambda *names: 100 * sum(e_by_type[n] for n in names) / total
    res = dict(
        time=meta.get("estimated printing time (normal mode)"),
        grams=meta.get("total filament used [g]") or meta.get("filament used [g]"),
        metres=round(float(meta.get("filament used [mm]", "0").split(",")[0]) / 1000, 2),
        support_pct=round(share("Support material", "Support material interface"), 1),
        bridge_pct=round(share("Bridge infill"), 1),
        layers=sum(1 for _ in open(gcode, encoding="utf-8", errors="replace") if _.startswith(";LAYER_CHANGE")),
    )
    for k, v in res.items():
        print(f"{k:12}: {v}")
    return res


if __name__ == "__main__":
    slice_part(sys.argv[1], sys.argv[2], sys.argv[3:])
