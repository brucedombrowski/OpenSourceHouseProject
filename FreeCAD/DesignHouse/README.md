BeachHouse workspace structure:
- `macros/` — FreeCAD macros (Build_950Surf, Make_950Surf_Lot, snapshot_pile_spacing, Show_All_and_Fit, export_bom_beach).
- `docs/` — project docs (`requirements.md`, `decisions.md`).
- `run_beach_house.sh` — build driver (uses macros in `macros/`).
- `macros/catalog.csv`, `macros/beach_bom.csv` — BeachHouse-specific catalog and BOM output.
- `builds/` — generated FCStd + snapshots.
