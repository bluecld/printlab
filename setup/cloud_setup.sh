#!/bin/bash
# printlab cloud environment setup: paste into the environment's Setup script box.
# Installs the CAD, mesh, render and slicer tools so every new session starts ready.
set -euo pipefail

# Slicers, fallback CAD, and the runtime libraries OrcaSlicer needs even headless
apt-get update -q
apt-get install -y -q prusa-slicer openscad libwebkit2gtk-4.1-0 libjavascriptcoregtk-4.1-0

# Python tools (pinned to the versions tested on 2026-10-30)
python3 -m venv /opt/printlab-venv
/opt/printlab-venv/bin/pip install -q \
  cadquery==2.8.0 trimesh==5.2.0 pyvista==0.49.2 vtk==9.6.2 \
  shapely==2.2.0 networkx==3.7 scipy==1.18.1 rtree==1.4.1 \
  matplotlib==3.11.2 numpy==2.5.4

# OrcaSlicer 2.4.2 (engine Creality Print is built on) from its SourceForge mirror, checksum-verified.
# Best effort: the mirror is slow (~10 min); if it fails, PrusaSlicer is still there.
ORCA_DIR="${ORCA_DIR:-/opt/orcaslicer}"
ORCA_FILE=OrcaSlicer_Linux_AppImage_Ubuntu2404_V2.4.2.AppImage
ORCA_SHA1=00383ed2f3a5a6e3c7066a3a1fe7052855c5f8ce
ORCA_CACHE="${ORCA_CACHE:-/tmp/$ORCA_FILE}"
orca_ok() { [ -f "$ORCA_CACHE" ] && echo "$ORCA_SHA1  $ORCA_CACHE" | sha1sum -c --quiet 2>/dev/null; }
if [ ! -x "$ORCA_DIR/squashfs-root/AppRun" ]; then
  orca_ok || curl -sSL -C - --retry 3 -m 1500 -o "$ORCA_CACHE" \
       "https://sourceforge.net/projects/orcaslicer.mirror/files/v2.4.2/$ORCA_FILE/download" || true
  if orca_ok; then
    mkdir -p "$ORCA_DIR" && cp "$ORCA_CACHE" "$ORCA_DIR/$ORCA_FILE" && chmod +x "$ORCA_DIR/$ORCA_FILE"
    (cd "$ORCA_DIR" && "./$ORCA_FILE" --appimage-extract > /dev/null)
    echo "printlab orcaslicer OK"
  else
    echo "printlab orcaslicer SKIPPED (download or checksum failed)"
  fi
fi

# Quick self-test: fails the setup if a required tool is missing
/opt/printlab-venv/bin/python -I -c "import cadquery, trimesh, pyvista, shapely; print('printlab python OK')"
prusa-slicer --help > /dev/null && echo "printlab slicer OK"
