# Beach House Decisions Log

Use lightweight entries (date, decision, rationale). Update as choices are made.

- TBD — first decision goes here.
- Coord system: Lot modeled in +X/+Y with origin at southwest corner; lot extents 50' (X) by 100' (Y); 5' setback on 50' side → buildable width 40'.
- Build routing: `FreeCAD/run_build_house.sh` with `BUILD_TARGET=beach` or `BEACH_LOT=1` invokes `BeachHouse/run_beach_house.sh` to generate 950 Surf lot (`FreeCAD/builds/950Surf.<timestamp>.fcstd`); default target remains lumber build.
- Lot setbacks: 5' on the 50' side (width), 20' front (road) setback along Y; buildable envelope is 40' wide by 80' deep (from Y=20' to Y=100').
- Pile spec: square 12"x12" treated piles, assume 40' total (20' embed, 20' above grade to bearing); supplier reference: American Pole & Timber.
- Pile grid: 6 piers along X evenly spaced across 40' buildable width (centers at edges); Y rows on 16' increments starting at Y=20' (front setback): 20', 36', 52', 68', 84' to support four 16' beams with splices at pier centers.
- Elevation: Z=0 at finished grade; piles modeled down to Z=-20' embed and up to Z=+20' bearing.
