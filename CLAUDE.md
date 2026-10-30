# printlab: CAD-to-print in the cloud (Creality K2)

Code-only pipeline: parametric CAD (CadQuery) -> checks -> renders -> STL -> slice (CLI) -> G-code.
No desktop apps, no screen control. Claude never starts a print; Anthony presses print.

## Printer and material
- Creality K2, 0.4 mm nozzle, Smooth PEI plate, CFS. Hyper PLA (default); Hyper PETG (new, untested).
- Profiles: Creality Print's own K2 profiles, from public repo CrealityOfficial/CrealityPrint (master,
  index version 26.07.18.18), in `profiles/creality_k2/source/` (inheritance resolved).
  - Printer: 260 x 260 x 260 mm, Klipper, max 800 mm/s, 20000 mm/s2, START_PRINT / END_PRINT macros.
  - Process: 0.20mm Standard @Creality K2 0.4 nozzle. Filament: Hyper PLA / Hyper PETG @Creality K2 0.4.
  - Smooth PEI = "hot_plate" temps: PLA 220 C nozzle / 50 C bed; PETG 250 / 70.
- Slicer (primary): OrcaSlicer 2.4.2 CLI, the engine Creality Print is built on, via `tools/slice_orca.py`
  with OrcaSlicer's bundled K2 profiles ("Creality K2 0.4 nozzle", "0.20mm Standard @Creality K2 0.4 nozzle",
  "Hyper PLA @K2-all" / "Hyper PETG @K2-all"), plate "High Temp Plate" (= Smooth PEI). Values match Creality
  Print's. Resolved presets actually used are saved in `profiles/creality_k2/orca/`.
  - Fix 1: retraction_distances_when_cut 30 -> 18 (bundled value is outside the CLI's 10-18 range; only used
    when the CFS cuts filament for a swap).
  - Fix 2: activate_chamber_temp_control off. Creality Print's K2 profile has support_chamber_temp_control = 0
    and never sends M191; OrcaSlicer would wait for a 30 C chamber before START_PRINT.
  - Output: Creality header block, START_PRINT EXTRUDER_TEMP/BED_TEMP, side fan (M106 P2), EXCLUDE_OBJECT,
    Klipper SET_VELOCITY_LIMIT. No exhaust fan (activate_air_filtration = 0, same as Creality Print). No thumbnails.
- Slicer (fallback): PrusaSlicer 2.7.2 CLI with `profiles/creality_k2/K2_0.4_<filament>_0.20_TEK.ini`
  (`tools/make_prusa_ini.py`, `tools/slice.py`). No side-fan commands; time estimate runs ~20% low vs OrcaSlicer.
- TEK overrides: 4 walls, 4 bottom / 5 top, 25% grid, supports Normal(auto) threshold 30 spacing 5, no brim, no skirt.
- Not yet verified on the printer: how the K2 maps T0 to a CFS slot for G-code not sent from Creality Print.
  First print from this chain: small part, watch the first layer.

## Workflow (every change)
1. Brief: function, key dimensions, what it mounts to. Max one multiple-choice question.
2. `parts/<name>/build_<name>_vN.py`: all dimensions in `P = dict(...)`. New version = copy to vN+1.
   Never edit or delete a released version.
3. Build: must print `OK all features built (...)` with the expected body count.
4. `tools/check.py` (watertight, bed fit, overhang < 45 deg, flat ceilings, tall/thin),
   `tools/render.py` (iso/front/back/side, overhangs red), `tools/section.py` (mating gaps).
5. Fix printability in CAD, not in the slicer.
6. Export one STL per body, copy to `_print.stl`.
7. `tools/slice_orca.py <PLA|PETG> <out_dir> <stl...>`: reports time, grams, support %, bridge %,
   and objects found vs expected. Check support % is where expected. (Fallback: `tools/slice.py`.)
8. Stop. Deliver files. Update this file.

## Environment (cloud container is wiped between sessions)
- Environment setup script = `setup/cloud_setup.sh` (pinned versions, self-test), saved to the
  "Default Cloud Environment" on 2026-10-30. Network access: Full. Python: `/opt/printlab-venv/bin/python -I`.
- The setup script installs tools only. Project files live in the private repo `bluecld/printlab`: start each
  session with that repository selected. First step in a new session: "check setup".
- Git: new work on a branch, one draft PR per change; Anthony merges. Never push to `main` directly.
- GitHub: this session only serves git source of public repos; release downloads are blocked per repository
  (allowed-domain list does not change that). Creality Print for Linux is GitHub-release only -> not reachable.
- OrcaSlicer 2.4.2 AppImage from SourceForge mirror (orcaslicer.mirror/v2.4.2, sha1 00383ed2f3a5a6e3c7066a3a1fe7052855c5f8ce)
  extracted to /opt/orcaslicer/squashfs-root; needs libwebkit2gtk-4.1-0 even headless. Setup script installs it
  (best effort; mirror is slow, ~10 min). Auto mode blocks running downloaded programs: switch the session to
  Accept edits and approve the OrcaSlicer prompt.
- PyVista renders off-screen (no display needed).

## Parts
| Part | Version | Bodies | Orientation | Status |
|---|---|---|---|---|
| fit_coupon | v1 | Rail, Slider | both flat as modelled, slots up | sliced, not printed |

## Print log
| Date | Part / version | Material | Settings | Time / grams / support | Result |
|---|---|---|---|---|---|
| 2026-10-30 | FitCoupon v1 plate (Rail + Slider) | Hyper PLA | TEK 0.20, PrusaSlicer + Creality K2 profile | 12m 26s / 8.20 g / 0 % | superseded by OrcaSlicer G-code |
| 2026-10-30 | FitCoupon v1 plate (Rail + Slider) | Hyper PLA | TEK 0.20, OrcaSlicer 2.4.2 + K2 profile, Smooth PEI | 15m 16s / 8.19 g / 0 % | not printed yet |

## Ideas list (not built yet)
- (empty) DecoMount on the PC was a sample only.
- Detent coupon: sliding fit with ~0.4 mm click bump on a flex arm (needs compliance; rigid bump would jam).

## Lessons learned
- Engraved text on a vertical wall makes tiny ceilings; slicer fills them with support that can't be removed.
  Put text on top faces. `check.py` now warns on any ceiling > 0.5 mm2.
- PrusaSlicer CLI with several STLs slices them as separate jobs (last one wins) unless `--merge`.
  `slice.py` adds it. Always confirm every object appears in the G-code.
- OrcaSlicer CLI error -17 (process not compatible): a flattened printer preset must be "from": "system" and
  the process must list it in compatible_printers. Error -18: a profile value is out of range; the message names it.
- Read the start of every new G-code: OrcaSlicer added an M191 chamber wait that Creality Print would not send.
