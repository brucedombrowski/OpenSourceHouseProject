# Double 3x5 Window Wall — Build Notes (in progress)

Work-in-progress instructions for assembling the 8' double 3x5 window wall macro set. Update this file as new steps are added.

## Orientation & Conventions
- Origin: lower-left corner of wall; wall runs along +Y; Z is vertical; X is wall thickness (1.5").
- Stock: 2x4x96 plates, 2x4x104.625 kings. Header/jack details will be added in later steps.
- Colors for iteration (ROYGBIV-inspired): bottom plate red, top plate orange, kings yellow (Step 1 macro).

## Current Step (in main macro)
- Macro: `Window_Wall_Double_3x5.FCMacro` (single file, iterated)
- Builds:
  - Bottom plate: 2x4x96 (1.5" x 3.5" x 96"), red
  - Top plate: 2x4x96, red
  - Left and right king studs: 2x4x104.625 (rotated 90°, face matches plates), yellow
  - Jacks: 2x4 cut to 80" just inside kings, green
  - Built-up header on top of jacks: 2x12x7'9" (2 plies, orange) + 0.5" rip 11.25x7'9" (blue) sandwiched between; sits at Z = plate_thick + 80", plies offset in X (0.0, +1.5, +2.0)
  - Cap plate atop header: 2x4x93 (red)
  - Short blocks atop header: qty 7 of 2x4x11-7/8" at 16" OC, teal (cut from 2x4x96 stock)
  - Bottom short studs: qty 7 of 2x4x15.5" at 16" OC along the bottom plate (starting at left jack face), violet (cut from 2x4x96 stock; first +1.5" Y, seventh -6" Y)
  - Cap atop bottom shorts: 2x4x90 (red), centered between jacks, sitting on the 15.5" studs
  - Second cap: another 2x4x90 (red) stacked above the first cap
  - 60" studs: qty 6 of 2x4x60 on the second cap (cut from 2x4x96 stock), layout: stud1 at cap_start (left face aligned to right face of left jack), stud2 = +36" from stud1, stud3 adjacent to stud2 (+1.5"), stud4 = stud3 + 15", stud5 adjacent to stud4 (+1.5"), stud6 = stud5 + 34.5" (36" minus 1.5") to fine-tune right alignment
  - Top cap over 60" studs: 2x4x90 (red), should align with header underside
- Usage: Open a new FreeCAD doc, run the macro, expect group `Window_Wall_Double_3x5` with colors keyed to dimensions.

## Upcoming Steps (to be added in the same macro)
- Add 80" jacks and built-up header: 2x12x7'9" (qty 2) + 0.5" rip at 11.25" x 7'9", sitting on jacks.
- Add sill, center post, rough openings, and cripples (above/below) per provided dimensions.
- Add optional sliding door variant derived from the same module dimensions.

Keep this document updated as each construction step is implemented.***
