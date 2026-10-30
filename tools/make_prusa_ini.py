"""Build PrusaSlicer .ini profiles for the Creality K2 from Creality Print's own K2 profiles.

Source: CrealityOfficial/CrealityPrint master, resources/profiles/Creality (resolved JSON in
profiles/creality_k2/source). Every machine limit comes from that source; nothing is invented.
TEK overrides (walls, shells, infill, supports, no brim) are in TEK below.

Usage: python -I make_prusa_ini.py <printlab root>
"""
import json, sys, pathlib

ROOT = pathlib.Path(sys.argv[1])
SRC = ROOT / "profiles/creality_k2/source"
OUT = ROOT / "profiles/creality_k2"

# TEK process overrides on top of "0.20mm Standard @Creality K2 0.4 nozzle"
TEK = dict(
    perimeters=4, bottom_solid_layers=4, top_solid_layers=5,
    fill_density="25%", fill_pattern="grid",
    support_material=1, support_material_auto=1, support_material_threshold=30,
    support_material_style="grid", support_material_spacing=5,
    brim_width=0, skirts=0,
)
# Smooth PEI plate = "hot_plate" temperatures in Creality Print profiles
PLATE = "hot_plate"


def load(name):
    return json.load(open(SRC / f"{name}.resolved.json", encoding="utf-8"))


def v(d, k):
    x = d[k]
    return x[0] if isinstance(x, list) else x


def pct_of(val, base):
    val = str(val)
    return round(float(base) * float(val[:-1]) / 100) if val.endswith("%") else float(val)


def translate_gcode(g):
    # Orca/Creality Print placeholders -> PrusaSlicer placeholders
    for a, b in (
        ("[nozzle_temperature_initial_layer]", "[first_layer_temperature]"),
        ("[bed_temperature_initial_layer_single]", "[first_layer_bed_temperature]"),
        ("[initial_no_support_extruder]", "[initial_tool]"),
        ('print_sequence == "by object"', "complete_objects"),
    ):
        g = g.replace(a, b)
    return g


def printer(m):
    area = v(m, "printable_area")
    return dict(
        printer_model="", printer_notes="Creality K2 0.4 (from Creality Print profile)",
        bed_shape=area, max_print_height=v(m, "printable_height"),
        nozzle_diameter=v(m, "nozzle_diameter"), gcode_flavor=v(m, "gcode_flavor"),
        use_relative_e_distances=v(m, "use_relative_e_distances"),
        machine_limits_usage="time_estimate_only",
        machine_max_acceleration_x=v(m, "machine_max_acceleration_x"),
        machine_max_acceleration_y=v(m, "machine_max_acceleration_y"),
        machine_max_acceleration_z=v(m, "machine_max_acceleration_z"),
        machine_max_acceleration_e=v(m, "machine_max_acceleration_e"),
        machine_max_acceleration_extruding=v(m, "machine_max_acceleration_extruding"),
        machine_max_acceleration_retracting=v(m, "machine_max_acceleration_retracting"),
        machine_max_acceleration_travel=v(m, "machine_max_acceleration_travel"),
        machine_max_feedrate_x=v(m, "machine_max_speed_x"),
        machine_max_feedrate_y=v(m, "machine_max_speed_y"),
        machine_max_feedrate_z=v(m, "machine_max_speed_z"),
        machine_max_feedrate_e=v(m, "machine_max_speed_e"),
        machine_max_jerk_x=v(m, "machine_max_jerk_x"), machine_max_jerk_y=v(m, "machine_max_jerk_y"),
        machine_max_jerk_z=v(m, "machine_max_jerk_z"), machine_max_jerk_e=v(m, "machine_max_jerk_e"),
        min_layer_height=v(m, "min_layer_height"), max_layer_height=v(m, "max_layer_height"),
        retract_length=v(m, "retraction_length"), retract_speed=v(m, "retraction_speed"),
        deretract_speed=v(m, "deretraction_speed"), retract_before_travel=v(m, "retraction_minimum_travel"),
        retract_layer_change=v(m, "retract_when_changing_layer"),
        retract_before_wipe=f'{v(m, "retract_before_wipe")}%', wipe=v(m, "wipe"),
        retract_lift=v(m, "z_hop"), retract_lift_below=v(m, "retract_lift_below"),
        autoemit_temperature_commands=0,
        start_gcode=translate_gcode(v(m, "machine_start_gcode")),
        end_gcode=translate_gcode(v(m, "machine_end_gcode")),
        before_layer_gcode=v(m, "before_layer_change_gcode"),
        layer_gcode="", thumbnails="96x96/PNG,300x300/PNG",
    )


def process(p):
    acc = float(v(p, "default_acceleration"))
    d = dict(
        layer_height=v(p, "layer_height"), first_layer_height=v(p, "initial_layer_print_height"),
        perimeters=v(p, "wall_loops"), top_solid_layers=v(p, "top_shell_layers"),
        bottom_solid_layers=v(p, "bottom_shell_layers"),
        fill_density=f'{v(p, "sparse_infill_density")}%', fill_pattern=v(p, "sparse_infill_pattern"),
        top_fill_pattern="monotonic", bottom_fill_pattern="monotonic",
        infill_anchor=v(p, "infill_anchor"), infill_anchor_max=v(p, "infill_anchor_max"),
        infill_overlap=v(p, "infill_wall_overlap"),
        extrusion_width=v(p, "line_width"), external_perimeter_extrusion_width=v(p, "outer_wall_line_width"),
        perimeter_extrusion_width=v(p, "inner_wall_line_width"),
        infill_extrusion_width=v(p, "sparse_infill_line_width"),
        solid_infill_extrusion_width=v(p, "internal_solid_infill_line_width"),
        top_infill_extrusion_width=v(p, "top_surface_line_width"),
        first_layer_extrusion_width=v(p, "initial_layer_line_width"),
        support_material_extrusion_width=v(p, "support_line_width"),
        external_perimeter_speed=v(p, "outer_wall_speed"), perimeter_speed=v(p, "inner_wall_speed"),
        infill_speed=v(p, "sparse_infill_speed"), solid_infill_speed=v(p, "internal_solid_infill_speed"),
        top_solid_infill_speed=v(p, "top_surface_speed"), gap_fill_speed=v(p, "gap_infill_speed"),
        bridge_speed=v(p, "bridge_speed"), support_material_speed=v(p, "support_speed"),
        support_material_interface_speed=v(p, "support_interface_speed"),
        travel_speed=v(p, "travel_speed"), first_layer_speed=v(p, "initial_layer_speed"),
        small_perimeter_speed=v(p, "small_perimeter_speed"),
        enable_dynamic_overhang_speeds=v(p, "enable_overhang_speed"),
        overhang_speed_0=v(p, "overhang_4_4_speed"), overhang_speed_1=v(p, "overhang_3_4_speed"),
        overhang_speed_2=v(p, "overhang_2_4_speed"), overhang_speed_3="100%",
        default_acceleration=acc,
        external_perimeter_acceleration=pct_of(v(p, "outer_wall_acceleration"), acc),
        perimeter_acceleration=pct_of(v(p, "inner_wall_acceleration"), acc),
        top_solid_infill_acceleration=pct_of(v(p, "top_surface_acceleration"), acc),
        solid_infill_acceleration=pct_of(v(p, "internal_solid_infill_acceleration"), acc),
        infill_acceleration=pct_of(v(p, "sparse_infill_acceleration"), acc),
        bridge_acceleration=pct_of(v(p, "bridge_acceleration"), acc),
        first_layer_acceleration=pct_of(v(p, "initial_layer_acceleration"), acc),
        travel_acceleration=pct_of(v(p, "travel_acceleration"), acc),
        perimeter_generator=v(p, "wall_generator"), thick_bridges=v(p, "thick_bridges"),
        elefant_foot_compensation=v(p, "elefant_foot_compensation"),
        seam_position=v(p, "seam_position"),
        support_material=v(p, "enable_support"), support_material_threshold=v(p, "support_threshold_angle"),
        support_material_contact_distance=v(p, "support_top_z_distance"),
        support_material_bottom_contact_distance=v(p, "support_bottom_z_distance"),
        support_material_interface_layers=v(p, "support_interface_top_layers"),
        support_material_bottom_interface_layers=v(p, "support_interface_bottom_layers"),
        support_material_interface_spacing=v(p, "support_interface_spacing"),
        support_material_spacing=v(p, "support_base_pattern_spacing"),
        support_material_xy_spacing=v(p, "support_object_xy_distance"),
        brim_width=v(p, "brim_width"), skirts=v(p, "skirt_loops"),
        gcode_label_objects="octoprint", gcode_comments=0, binary_gcode=0,
        output_filename_format="{input_filename_base}.gcode",
    )
    d.update(TEK)
    return d


def filament(f):
    return dict(
        filament_settings_id=v(f, "name") if "name" in f else "",
        filament_type=v(f, "filament_type"), filament_diameter=v(f, "filament_diameter"),
        filament_density=v(f, "filament_density"), filament_cost=v(f, "filament_cost"),
        extrusion_multiplier=v(f, "filament_flow_ratio"),
        filament_max_volumetric_speed=v(f, "filament_max_volumetric_speed"),
        filament_retract_length=v(f, "filament_retraction_length"),
        temperature=v(f, "nozzle_temperature"), first_layer_temperature=v(f, "nozzle_temperature_initial_layer"),
        bed_temperature=v(f, f"{PLATE}_temp"), first_layer_bed_temperature=v(f, f"{PLATE}_temp_initial_layer"),
        cooling=1, fan_always_on=1,
        min_fan_speed=v(f, "fan_min_speed"), max_fan_speed=v(f, "fan_max_speed"),
        bridge_fan_speed=v(f, "overhang_fan_speed"),
        disable_fan_first_layers=v(f, "close_fan_the_first_x_layers"),
        fan_below_layer_time=v(f, "fan_cooling_layer_time"),
        slowdown_below_layer_time=v(f, "slow_down_layer_time"), min_print_speed=v(f, "slow_down_min_speed"),
        start_filament_gcode="; filament start gcode", end_filament_gcode="; filament end gcode",
    )


def write(path, *sections, header):
    lines = [f"# {h}" for h in header]
    for sec in sections:
        for k, val in sec.items():
            val = str(val).replace("\r", "").replace("\n", "\\n")
            lines.append(f"{k} = {val}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


m = load("Creality_K2_0.4_nozzle")
p = load("0.20mm_Standard_at_Creality_K2_0.4_nozzle")
for tag, fname in (("HyperPLA", "Hyper_PLA_at_Creality_K2_0.4_nozzle"), ("HyperPETG", "Hyper_PETG_at_Creality_K2_0.4_nozzle")):
    f = load(fname)
    out = OUT / f"K2_0.4_{tag}_0.20_TEK.ini"
    write(out, printer(m), process(p), filament(f), header=[
        f"Creality K2 0.4 / 0.20mm Standard / {v(f, 'name') if 'name' in f else tag} / Smooth PEI ({PLATE})",
        "Generated by tools/make_prusa_ini.py from Creality Print profiles (CrealityOfficial/CrealityPrint master).",
        "TEK overrides: " + ", ".join(f"{k}={val}" for k, val in TEK.items()),
    ])
    print("wrote", out.name)
