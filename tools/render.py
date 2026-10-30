"""Render iso / front / back / side PNGs of one or more STLs (print orientation, Z up), off-screen.

Faces that overhang more than 45 deg from vertical are drawn red so printability shows at a glance.
Usage: python -I render.py <out_prefix> <a.stl> [b.stl ...]
Writes <out_prefix>_iso.png, _front.png, _back.png, _side.png and _sheet.png (all four).
"""
import sys, math, numpy as np, pyvista as pv

pv.OFF_SCREEN = True
COLORS = ["#8fb3d9", "#c9b37e", "#9cc79a", "#c99ac7"]
OVERHANG = "#d9534f"
# camera direction (from object toward camera), view-up
VIEWS = {"iso": ((-1, -1.3, 1), (0, 0, 1)), "front": ((0, -1, 0), (0, 0, 1)),
         "back": ((0, 1, 0), (0, 0, 1)), "side": ((1, 0, 0), (0, 0, 1))}


def add(p, paths):
    for i, path in enumerate(paths):
        m = pv.read(path).compute_normals(cell_normals=True, point_normals=False)
        nz = m.cell_data["Normals"][:, 2]
        zc = m.cell_centers().points[:, 2]
        over = (nz < -math.cos(math.radians(45)) - 1e-3) & (zc > m.bounds[4] + 0.05)
        if over.any():
            m.cell_data["over"] = over.astype(int)
            p.add_mesh(m, scalars="over", cmap=[COLORS[i % len(COLORS)], OVERHANG], clim=(0, 1),
                       show_scalar_bar=False, smooth_shading=False)
        else:
            p.add_mesh(m, color=COLORS[i % len(COLORS)])


def shot(p, direction, up):
    p.camera_position = "xy"
    c = np.array(p.bounds).reshape(3, 2).mean(axis=1)
    d = np.array(direction, float); d /= np.linalg.norm(d)
    p.camera.focal_point = c
    p.camera.position = c + d * 500
    p.camera.up = up
    p.reset_camera()


def main(prefix, paths):
    for name, (d, up) in VIEWS.items():
        p = pv.Plotter(off_screen=True, window_size=(900, 700))
        p.set_background("white")
        add(p, paths)
        shot(p, d, up)
        p.add_text(name, font_size=12, color="black")
        p.screenshot(f"{prefix}_{name}.png")
        p.close()
    p = pv.Plotter(off_screen=True, shape=(2, 2), window_size=(1400, 1100))
    p.set_background("white")
    for i, (name, (d, up)) in enumerate(VIEWS.items()):
        p.subplot(i // 2, i % 2)
        add(p, paths)
        shot(p, d, up)
        p.add_text(name + ("   (red = overhang < 45 deg)" if i == 0 else ""), font_size=11, color="black")
    p.screenshot(f"{prefix}_sheet.png")
    p.close()
    print("rendered", prefix + "_{iso,front,back,side,sheet}.png")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2:])
