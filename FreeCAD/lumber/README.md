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
  - `ln -s <repo>/FreeCAD/lumber/joists_from_catalog.FCMacro ~/.FreeCAD/Macro/`
- After setting the macro path or symlink, the macros (e.g., `joists_from_catalog.FCMacro`) should appear in the Macro dialog without manual import.
