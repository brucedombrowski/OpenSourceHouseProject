Pricing Agent Instructions
==========================

Goal: Populate pricing and links so the BOM shows costs.

File to edit
- `FreeCAD/BeachHouse/macros/catalog.csv`

What to fill in (per row/label)
- `supplier`: e.g., `lowes`
- `sku`: Lowe’s item number
- `url`: product link
- Price: use either
  - `price_each_usd` (fixed-price items), or
  - `price_per_ft_usd` (for per-foot lumber). Length is already provided in `length_in` for most items.

Special cases
- Piles already default to $1000 each; override if you have a better number.

Steps
1) Update `macros/catalog.csv` with real `supplier`, `sku`, `url`, and price columns as above.
2) Run `run_beach_house.sh` to regenerate the BOM (`builds/beach_bom*.csv`) with totals.

Notes
- Keep the header as-is: `label,nominal,actual_thickness_in,actual_width_in,length_in,supplier,sku,url,price_each_usd,price_per_ft_usd`.
- The BOM exporter pulls prices/links from this file and computes `price_ext_usd` automatically.
