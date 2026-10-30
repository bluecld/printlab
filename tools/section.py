"""Cross-section check: cut one or more STLs with a plane and plot the outlines, with optional offsets
so mating parts can be placed together (e.g. a slider in its slot) and the gaps read off.

Usage: python -I section.py <out.png> <axis x|y|z> <position> <a.stl>[@dx,dy,dz] [b.stl@dx,dy,dz ...]
Prints the smallest gap between each pair of parts in the section.
"""
import sys, numpy as np, trimesh, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from shapely.geometry import Polygon
from shapely.ops import unary_union

COLORS = ["#4a78a8", "#b08a3c", "#4f9a4c", "#9a4f97"]
AXES = {"x": (0, (1, 2)), "y": (1, (0, 2)), "z": (2, (0, 1))}


def cut(path, axis, pos, off):
    m = trimesh.load(path, force="mesh")
    m.apply_translation(off)
    i, keep = AXES[axis]
    normal = np.zeros(3); normal[i] = 1
    origin = np.zeros(3); origin[i] = pos
    sec = m.section(plane_origin=origin, plane_normal=normal)
    if sec is None:
        return None
    polys = []
    for ent in sec.discrete:
        pts = ent[:, keep]
        if len(pts) > 2:
            polys.append(Polygon(pts).buffer(0))
    return unary_union(polys) if polys else None


def main(out, axis, pos, specs):
    shapes = []
    fig, ax = plt.subplots(figsize=(10, 5), dpi=130)
    for k, spec in enumerate(specs):
        path, _, o = spec.partition("@")
        off = [float(v) for v in o.split(",")] if o else [0, 0, 0]
        s = cut(path, axis, float(pos), off)
        shapes.append((path.split("/")[-1], s))
        if s is None:
            continue
        for g in getattr(s, "geoms", [s]):
            x, y = g.exterior.xy
            ax.fill(x, y, color=COLORS[k % 4], alpha=0.55, lw=0.8, ec="black")
            for h in g.interiors:
                hx, hy = h.xy
                ax.fill(hx, hy, color="white", lw=0.8, ec="black")
    ax.set_aspect("equal"); ax.grid(alpha=0.3)
    ax.set_title(f"section {axis} = {pos} mm")
    fig.savefig(out, bbox_inches="tight", facecolor="white")
    for a in range(len(shapes)):
        for b in range(a + 1, len(shapes)):
            (na, sa), (nb, sb) = shapes[a], shapes[b]
            if sa is not None and sb is not None:
                over = sa.intersection(sb).area
                print(f"{na} vs {nb}: min gap {sa.distance(sb):.3f} mm, overlap {over:.3f} mm2")
    print("wrote", out)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4:])
