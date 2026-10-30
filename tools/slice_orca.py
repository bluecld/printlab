"""Slice with OrcaSlicer CLI (the engine Creality Print is built on) using OrcaSlicer's bundled
Creality K2 profiles plus the TEK overrides, then read the result.

Usage: python -I slice_orca.py <PLA|PETG> <out_dir> <a_print.stl> [b_print.stl ...]
Writes the resolved profiles used to <printlab>/profiles/creality_k2/orca/, the G-code to <out_dir>,
and reports time, grams, support %, bridge %.
"""
import os, sys, json, re, pathlib, subprocess, collections, shutil


def find_orca():
    """OrcaSlicer folder and executable: $PRINTLAB_ORCA, else the pinned portable copy or the normal
    install on Windows (same order as setup/win_setup.ps1), else the cloud container's AppImage."""
    if os.name == "nt":
        dirs = [os.environ.get("PRINTLAB_ORCA"), os.path.expandvars(r"%LOCALAPPDATA%\printlab\OrcaSlicer"),
                os.path.expandvars(r"%ProgramFiles%\OrcaSlicer")]
        exe = "orca-slicer.exe"
    else:
        dirs, exe = [os.environ.get("PRINTLAB_ORCA"), "/opt/orcaslicer/squashfs-root"], "AppRun"
    for d in filter(None, dirs):
        if (pathlib.Path(d) / exe).exists():
            return pathlib.Path(d), pathlib.Path(d) / exe
    raise SystemExit("OrcaSlicer not found (set PRINTLAB_ORCA to its folder)")


ORCA, ORCA_EXE = find_orca()
PROFILES = ORCA / "resources/profiles"
ROOT = pathlib.Path(__file__).resolve().parent.parent
SAVE = ROOT / "profiles/creality_k2/orca"

MACHINE = "Creality K2 0.4 nozzle"
PROCESS = "0.20mm Standard @Creality K2 0.4 nozzle"
FILAMENT = {"PLA": "Hyper PLA @K2-all", "PETG": "Hyper PETG @K2-all"}
BED = "High Temp Plate"   # = Smooth PEI plate (uses hot_plate_temp)

# Bundled K2 profile ships retraction_distances_when_cut = 30, outside the CLI's allowed 10-18
# (error -18). Only used when the CFS cuts filament for a swap; clamp to the max allowed.
MACHINE_FIX = dict(retraction_distances_when_cut=["18"])
# Creality Print's K2 machine profile has support_chamber_temp_control = 0, so it never sends
# M191 (heat chamber and wait). OrcaSlicer would, from the filament's chamber setting; match CP.
FILAMENT_FIX = dict(activate_chamber_temp_control=["0"])

# TEK overrides on top of the stock 0.20mm Standard process
TEK = dict(
    wall_loops="4", bottom_shell_layers="4", top_shell_layers="5",
    sparse_infill_density="25%", sparse_infill_pattern="grid",
    enable_support="1", support_type="normal(auto)", support_threshold_angle="30",
    support_base_pattern_spacing="5", brim_type="no_brim", skirt_loops="0",
)


def resolve(name):
    idx = json.load(open(PROFILES / "Creality.json", encoding="utf-8"))
    paths = {e["name"]: e["sub_path"] for k in ("machine_list", "machine_model_list", "process_list", "filament_list")
             for e in idx.get(k, [])}
    d = json.load(open(PROFILES / "Creality" / paths[name], encoding="utf-8"))
    base = resolve(d["inherits"]) if d.get("inherits") else {}
    base.update({k: v for k, v in d.items() if k != "inherits"})
    return base


def write_profiles(material):
    SAVE.mkdir(parents=True, exist_ok=True)
    out = {}
    for kind, name, extra in (("machine", MACHINE, MACHINE_FIX), ("process", PROCESS, TEK), ("filament", FILAMENT[material], FILAMENT_FIX)):
        d = resolve(name)
        d.update(extra)
        # The CLI matches the process's compatible_printers against the printer's system name,
        # which for a user preset is its "inherits". These presets are flattened (no inherits),
        # so the printer stays marked "system" (it is Creality's profile, unchanged) and the
        # process/filament list it by name; otherwise the CLI exits with -17 (not compatible).
        d.update({"from": "system" if kind == "machine" else "User", "is_custom_defined": "0"})
        if kind != "machine":
            d["compatible_printers"] = [MACHINE]
            d["compatible_printers_condition"] = ""
        tag = {"machine": "K2_0.4", "process": "0.20_TEK", "filament": f"Hyper{material}_K2"}[kind]
        out[kind] = SAVE / f"orca_{kind}_{tag}.json"
        out[kind].write_text(json.dumps(d, indent=1), encoding="utf-8", newline="\n")
    return out


def run(material, out_dir, stls):
    prof = write_profiles(material)
    out_dir = pathlib.Path(out_dir); out_dir.mkdir(parents=True, exist_ok=True)
    work = out_dir / "_orca"; shutil.rmtree(work, ignore_errors=True); work.mkdir()
    cmd = [str(ORCA_EXE), "--arrange", "1", "--orient", "0", "--curr-bed-type", BED,
           "--load-settings", f"{prof['machine']};{prof['process']}", "--load-filaments", str(prof["filament"]),
           "--slice", "0", "--outputdir", str(work), *stls]
    r = subprocess.run(cmd, capture_output=True, encoding="utf-8", errors="replace", timeout=600)
    gcodes = sorted(work.glob("*.gcode"))
    if r.returncode or not gcodes:
        print(r.stdout[-3000:], r.stderr[-3000:])
        raise SystemExit(f"SLICE FAILED (exit {r.returncode})")
    # FitCoupon_v1_Rail_print -> FitCoupon_v1 for a plate; Bracket_v2_print -> Bracket_v2 for one body
    stem = pathlib.Path(stls[0]).stem.removesuffix("_print")
    if len(stls) > 1:
        stem = stem.rsplit("_", 1)[0]
    final = out_dir / f"{stem}_plate_Hyper{material}_orca.gcode"
    shutil.move(str(gcodes[0]), final)
    shutil.rmtree(work, ignore_errors=True)
    return read(final, [pathlib.Path(s).name for s in stls])


def read(gcode, names):
    e_by_type, meta, objects = collections.Counter(), {}, set()
    kind = "other"
    text = open(gcode, encoding="utf-8", errors="replace").read().splitlines()
    for line in text:
        if line.startswith(";TYPE:") or line.startswith("; FEATURE:"):
            kind = line.split(":", 1)[1].strip()
        elif line.startswith("G1") and " E" in line:
            m = re.search(r" E(-?[\d.]+)", line)
            if m and float(m.group(1)) > 0:
                e_by_type[kind] += float(m.group(1))
        elif line.startswith(";") and ("=" in line or ":" in line):
            k, _, v = line.lstrip("; ").partition(" = ") if " = " in line else line.lstrip("; ").partition(": ")
            meta.setdefault(k.strip(), v.strip())
        if "EXCLUDE_OBJECT_DEFINE" in line or line.startswith("; printing object"):
            objects.add(line)
    total = sum(e_by_type.values()) or 1
    share = lambda pat: round(100 * sum(v for k, v in e_by_type.items() if re.search(pat, k, re.I)) / total, 1)
    res = dict(
        time=meta.get("estimated printing time (normal mode)") or meta.get("model printing time"),
        grams=meta.get("total filament weight [g]") or meta.get("filament used [g]") or meta.get("total filament used [g]"),
        support_pct=share(r"support"), bridge_pct=share(r"bridge"),
        layers=meta.get("total layer number") or meta.get("total layers count"),
        objects_found=sum(1 for n in names if any(n.rsplit(".", 1)[0] in o for o in objects)),
        objects_expected=len(names),
    )
    for k, v in res.items():
        print(f"{k:16}: {v}")
    print("gcode           :", gcode)
    return res


if __name__ == "__main__":
    run(sys.argv[1].upper(), sys.argv[2], sys.argv[3:])
