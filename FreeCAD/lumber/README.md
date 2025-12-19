## Lumber Library (FreeCAD)

Goal: a parametric library of common dimensional lumber with supplier-aware metadata. Default supplier is Lowe's, but the schema supports Home Depot (or others) via extra columns.

### Data Schema (CSV)

Create/maintain `lumber_catalog.csv` with rows per stock size/length:

```
label, nominal, actual_thickness_in, actual_width_in, length_in, treatment, sku_lowes, url_lowes, sku_hd, url_hd
2x4x96, 2x4, 1.5, 3.5, 96, SPF, TBD, TBD, ,
2x4x104.625, 2x4, 1.5, 3.5, 104.625, SPF, TBD, TBD, ,
```

Columns:
- `label`: ID for the stock (e.g., 2x4x96, 2x6x96, 2x4x104.625)
- `nominal`: nominal size string (e.g., 2x4)
- `actual_thickness_in`, `actual_width_in`: actual dimensions (inches)
- `length_in`: board length (inches)
- `treatment`: e.g., SPF, PT (pressure treated), etc.
- `sku_lowes`, `url_lowes`: supplier-specific fields (optional per row)
- `sku_hd`, `url_hd`: Home Depot (optional; add more suppliers by adding more `sku_*`/`url_*` columns)

Notes:
- Default supplier is Lowe's; populate `sku_lowes`/`url_lowes` when available. Home Depot fields are placeholders for future use.
- Actual dimensions use the typical dressed sizes (e.g., 2x4 → 1.5" x 3.5").

### FreeCAD Usage

1) Create a master FreeCAD file (e.g., `lumber_library.FCStd`) that reads `lumber_catalog.csv`.
2) For each row, define a Body/Part driven by spreadsheet values; set custom properties:
   - `Label` = `label`
   - `Supplier` = current supplier tag (default: `lowes`)
   - `SKU`/`URL` = chosen supplier's columns for the row
3) Instantiate parts via Link/Clone in downstream models; a BOM macro will count Links/Clones and emit supplier-specific CSV.

### BOM Export (planned)

Provide a macro (e.g., `export_bom.FCMacro`) that:
- Takes a `supplier` parameter (default `lowes`)
- Traverses the document, counts occurrences of library parts
- Emits `label, quantity, sku_<supplier>, url_<supplier>, length_in` to CSV

### Next Steps
- Populate `lumber_catalog.csv` with common dimensional sizes/lengths (2x4/2x6/2x8/2x10/2x12 @ 8/10/12/16 ft, pre-cut studs 92 5/8 and 104 5/8).
- Add `lumber_library.FCStd` scaffold and a simple BOM macro honoring the `supplier` flag.

### Using project macros in FreeCAD
- Point FreeCAD’s macro search path to this repository’s `FreeCAD/lumber/` folder:
  - FreeCAD → Preferences → Macros → “Macro path” → set to `<repo>/FreeCAD/lumber/`
- Or symlink/copy macros into your user macro folder (e.g., `~/.FreeCAD/Macro` on Linux/Mac):
- `ln -s <repo>/FreeCAD/lumber/Joist_Module_2x12_16x16.FCMacro ~/.FreeCAD/Macro/`
- `ln -s <repo>/FreeCAD/lumber/Joist_Module_2x12_16x8.FCMacro ~/.FreeCAD/Macro/`
- `ln -s <repo>/FreeCAD/lumber/Sheathing_Advantech_4x8_16x24.FCMacro ~/.FreeCAD/Macro/`
- `ln -s <repo>/FreeCAD/lumber/Build_House_16x24_From_Modules.FCMacro ~/.FreeCAD/Macro/`
- `ln -s <repo>/FreeCAD/lumber/Wall_2x4_16ft.FCMacro ~/.FreeCAD/Macro/`
- `ln -s <repo>/FreeCAD/lumber/Window_Wall_Double_3x5.FCMacro ~/.FreeCAD/Macro/`
- `ln -s <repo>/FreeCAD/lumber/Window_Wall_Double_3x5_Step1.FCMacro ~/.FreeCAD/Macro/`
- `ln -s <repo>/FreeCAD/lumber/Sliding_Door_72x80.FCMacro ~/.FreeCAD/Macro/`
- After setting the macro path or symlink, the macros (e.g., `Joist_Module_2x12_16x16.FCMacro`, `Joist_Module_2x12_16x8.FCMacro`, `Sheathing_Advantech_4x8_16x24.FCMacro`, `Build_House_16x24_From_Modules.FCMacro`) should appear in the Macro dialog without manual import.

## House assembly macro
- `Build_House_16x24_From_Modules.FCMacro` assembles the 16x24 footprint: two joist modules (16x16 + 16x8), 0.5" plywood shim on the rim edge, sheathing footprint widened to 195.5" to cover the shim, front/back window + sliding door modules (rotated and placed), short side walls (8'−3.5") with 16" OC studs, and direction-agnostic module names grouped under Front/Back/Left/Right wall groups. A single added top-plate layer (2x4 segments, 16' plus remainders) runs the perimeter atop the first-floor walls with staggered seams.

## Stud wall macro
- `Wall_2x4_16ft.FCMacro` builds a straight 16' wall with 2x4x192 plates and 2x4x104.625 studs laid out at 16" OC. It creates a `Wall_2x4_16ft` group at the origin with Z=0 on the bottom plate; move/rotate it in assemblies as needed. `Build_House_16x24_From_Modules.FCMacro` now calls this macro and places the wall on top of the sheathing, inset 1.5" from the rims.

## Window wall macro
- `Window_Wall_Double_3x5.FCMacro` builds an 8' wide double-window wall: 2x4x96 plates, 104.625" king studs (ends + header kings + center), 80" jack studs under a cut 2x12 header (90" span), sill at 20", window rough openings 36" wide x 60" tall (two openings with a 1.5" center post), and cripple studs above/below. Group name `Window_Wall_Double_3x5`, origin at lower-left corner with wall running +Y.
- `Window_Wall_Double_3x5_Step1.FCMacro` is the minimal starting state: top/bottom 2x4x96 plates and left/right 104.625" kings only, with ROYGBIV colors for clarity. Group `Window_Wall_Double_3x5_Step1`, origin at lower-left.

## Sliding door macro
- `Sliding_Door_72x80.FCMacro` builds plates, end kings, 80" jacks, a 93" built-up header (2x12 + 0.5" ply + 2x12) with cap plate, 16" OC header blocks, and six 80" studs laid out to center a 72" opening. Origin at lower-left, wall runs +Y.

## Hardware
- Joist hangers: placeholder label `hanger_LU210` (approx 16ga, 12" height, 2" seat depth) modeled as a simple U-shape for BOM counting; attached automatically to joist modules.

## Future improvement: face-based snapping
- Current placement uses explicit offsets (plates, walls, roof, porch). A future pass should read target faces/planes (e.g., ridge faces, plate tops) and snap parts to those, to avoid manual X/Z nudges.
- Candidate helpers: `place_against_face(obj, target_face, axis="Z")` for vertical seating, and `snap_end_to_face(obj, face, along_axis)` for rafters/ridge alignment.
- Apply to: rafter-to-ridge, rafters to plates, wall-to-sheathing, porch rafters to ledger/beam.
