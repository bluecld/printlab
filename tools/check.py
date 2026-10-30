"""Printability check for an STL in print orientation (Z up, bed at min Z).

Usage: python -I check.py <part.stl> [--bed 260x260x260]
Prints a report and exits 1 if a hard limit fails (not watertight, does not fit the bed).
"""
import sys, math, numpy as np, trimesh

SELF_SUPPORT_DEG = 45      # faces flatter than this (from horizontal) need support
FLAT_CEILING_DEG = 10      # near-horizontal ceilings: flag for Normal (grid) supports
TALL_RATIO = 3.0           # height / smallest footprint side above this -> tipping risk


def report(path, bed=(260, 260, 260)):
    m = trimesh.load(path, force="mesh")
    bodies = m.split(only_watertight=False)
    lo, hi = m.bounds
    size = hi - lo
    n = m.face_normals
    a = m.area_faces
    zc = m.triangles_center[:, 2]
    on_bed = zc < lo[2] + 0.05
    down = (n[:, 2] < -math.cos(math.radians(SELF_SUPPORT_DEG)) - 1e-3) & ~on_bed
    flat = (n[:, 2] < -math.cos(math.radians(FLAT_CEILING_DEG))) & ~on_bed
    foot = trimesh.Trimesh(m.vertices, m.faces[on_bed & (n[:, 2] < -0.99)]) if on_bed.any() else None
    foot_area = a[on_bed & (n[:, 2] < -0.99)].sum()
    foot_xy = (foot.bounds[1] - foot.bounds[0])[:2] if foot is not None and len(foot.faces) else np.zeros(2)
    ratio = size[2] / max(min(foot_xy), 1e-6) if foot_area else float("inf")

    fails, warns = [], []
    if not m.is_watertight:
        fails.append("mesh is not watertight")
    if any(size[i] > bed[i] for i in range(3)):
        fails.append(f"does not fit the bed {bed}")
    if a[flat].sum() > 25:
        warns.append(f"flat ceiling over open space {a[flat].sum():.0f} mm2: needs Normal (grid) supports, not tree")
    elif a[flat].sum() > 0.5:
        warns.append(f"small ceilings {a[flat].sum():.1f} mm2 (z={zc[flat].min():.1f}): slicer will add support there, "
                     "e.g. inside engraved text on a wall")
    if a[down].sum() > 5:
        warns.append(f"overhang below {SELF_SUPPORT_DEG} deg: {a[down].sum():.0f} mm2 (lowest at z={zc[down].min():.1f})")
    if ratio > TALL_RATIO:
        warns.append(f"tall/thin: height {size[2]:.1f} vs footprint {min(foot_xy):.1f} mm (ratio {ratio:.1f}): add footprint or brim")

    print(f"file        : {path}")
    print(f"bodies      : {len(bodies)}   watertight: {m.is_watertight}")
    print(f"size  XYZ   : {size[0]:.2f} x {size[1]:.2f} x {size[2]:.2f} mm")
    print(f"volume      : {m.volume/1000:.2f} cm3")
    print(f"footprint   : {foot_area:.0f} mm2")
    print(f"overhang    : {a[down].sum():.0f} mm2 below {SELF_SUPPORT_DEG} deg, flat ceilings {a[flat].sum():.0f} mm2")
    for w in warns:
        print("WARN  " + w)
    for f in fails:
        print("FAIL  " + f)
    print("CHECK " + ("FAILED" if fails else "OK"))
    return not fails


if __name__ == "__main__":
    bed = (260, 260, 260)
    if "--bed" in sys.argv:
        bed = tuple(float(x) for x in sys.argv[sys.argv.index("--bed") + 1].split("x"))
    sys.exit(0 if report(sys.argv[1], bed) else 1)
