"""Dovetail fit coupon v1: one rail block with three slots (clearance 0.10 / 0.15 / 0.20 mm per side)
and one slider that tests all three. Print both flat, as modelled. No supports needed.

Usage: python -I build_fit_coupon_v1.py <out_dir>
"""
import sys, math, pathlib
import cadquery as cq

P = dict(
    length=25.0,          # slot / slider length (Y)
    depth=4.0,            # dovetail depth
    base_w=11.0,          # dovetail width at the bottom (wide side)
    flank_deg=60.0,       # flank angle from horizontal (>= 45 so the undercut self-supports)
    clearances=(0.10, 0.15, 0.20),   # per side, normal to the faces
    pitch=18.0,           # slot spacing (X)
    floor=3.0,            # material under the slots
    label_strip=6.0,      # solid strip at the front end of each slot that carries its label (slot = stop)
    neck_h=4.0,           # slider neck above the rail
    edge_r=0.8,           # round on outer vertical edges
    lead_in=0.6,          # chamfer on slider ends so it starts easily
    label_h=3.0, label_depth=0.6,
)

OUT = pathlib.Path(sys.argv[1]); OUT.mkdir(parents=True, exist_ok=True)
step = "start"
try:
    run = P["depth"] / math.tan(math.radians(P["flank_deg"]))
    top_w = P["base_w"] - 2 * run
    assert top_w >= 3.0, f"slider neck {top_w:.2f} mm < 3 mm"

    def trapezoid(off, z_top):
        # dovetail profile in XZ, bottom at z=0: flank x(z) = base_w/2 - z*cot, offset outward by `off`
        # normal to every face; returns bottom at z=-off and flanks carried up to z_top
        th = math.radians(P["flank_deg"])
        x = lambda z: P["base_w"] / 2 + off / math.sin(th) - z / math.tan(th)
        return [(-x(-off), -off), (x(-off), -off), (x(z_top), z_top), (-x(z_top), z_top)]

    step = "rail block"
    n = len(P["clearances"])
    W, H = n * P["pitch"], P["floor"] + P["depth"]
    rail = cq.Workplane("XY").box(W, P["length"], H, centered=(True, True, False)).edges("|Z").fillet(P["edge_r"])

    step = "slots"
    for i, c in enumerate(P["clearances"]):
        x = (i - (n - 1) / 2) * P["pitch"]
        # flanks run 1 mm past the top face so the cut is clean
        pts = [(x + px, P["floor"] + pz) for px, pz in trapezoid(c, P["depth"] + 1)]
        slot = cq.Workplane("XZ").polyline(pts).close().extrude(P["length"] / 2 + 1, both=True)
        # slot is open at the back, closed by the label strip at the front
        keep = cq.Workplane("XY").box(W + 2, P["length"] - P["label_strip"] + 1, H + 4, centered=(True, False, False)) \
            .translate((0, -P["length"] / 2 + P["label_strip"], -1))
        rail = rail.cut(slot.intersect(keep))

    step = "labels"
    # engraved into the top face in line with each slot: no overhang, no supports, can't be misread
    for i, c in enumerate(P["clearances"]):
        x = (i - (n - 1) / 2) * P["pitch"]
        txt = (cq.Workplane("XY").workplane(offset=H).center(x, -P["length"] / 2 + P["label_strip"] / 2)
               .text(f"{c:.2f}"[1:], P["label_h"], -P["label_depth"], combine=False,
                     halign="center", valign="center"))
        rail = rail.cut(txt)

    step = "slider"
    prof = trapezoid(0, P["depth"])
    neck = [(-top_w / 2, P["depth"]), (top_w / 2, P["depth"]), (top_w / 2, P["depth"] + P["neck_h"]), (-top_w / 2, P["depth"] + P["neck_h"])]
    slider = cq.Workplane("XZ").polyline(prof).close().extrude(P["length"] / 2, both=True)
    slider = slider.union(cq.Workplane("XZ").polyline(neck).close().extrude(P["length"] / 2, both=True))
    slider = slider.faces("<Y or >Y").edges().chamfer(P["lead_in"] * 0.5)

    step = "export"
    for name, body in (("Rail", rail), ("Slider", slider)):
        solids = body.solids().size()
        assert solids == 1, f"{name}: {solids} solids"
        cq.exporters.export(body, str(OUT / f"FitCoupon_v1_{name}.step"))
        cq.exporters.export(body, str(OUT / f"FitCoupon_v1_{name}.stl"), tolerance=0.01, angularTolerance=0.1)
    print(f"slider neck {top_w:.2f} mm, rail {W:.0f} x {P['length']:.0f} x {H:.0f} mm")
    print("OK all features built (2 bodies: Rail, Slider)")
except Exception as e:
    print(f"FAILED at step {step}: {e}")
    sys.exit(1)
