# Sliding Door 72x80 — Step-by-Step Build

Human-ready instructions to frame the 8' sliding door module in the field. The FreeCAD macro can generate snapshots for each stage; drop those images under the matching steps below. Orientation matches the macro: origin at lower-left, wall runs +Y, Z is vertical, X is wall thickness (1.5").

## Cut List
- Plates: (2) 2x4x96 (bottom/top)
- End kings: (2) 2x4x104.625 (rotate to 3.5" face out)
- Jacks: (2) 2x4 cut to 80" (support header)
- Header: 93" built-up — (2) 2x12x93 + (1) 0.5" ply rip 11.25"x93
- Cap on header: (1) 2x4x93
- Header blocks: (7) 2x4 cut to 11-7/8"
- Studs for RO layout: (6) 2x4 cut to 80"

## Layout & Framing
1) **Lay out plates** — Mark 0" at the left end of the bottom plate. Snap a centerline at 48" (module midpoint). [Snapshot: plates]
2) **Set kings** — Place 104-5/8" kings at Y=0" and Y=94.5" (outer faces); nail to plates. [Snapshot: plates+kings]
3) **Install jacks** — Place 80" jacks tight to inside faces at Y=1.5" and Y=93"; nail to plates and kings. These define the header support points. [Snapshot: add jacks]
4) **Assemble header** — Sandwich 0.5" ply between two 2x12x93; glue/nail per local code. Set the built-up header on the jacks at Z=1.5"+80". [Snapshot: header set]
5) **Cap the header** — Add the 2x4x93 cap on top of the built-up header. [Snapshot: cap plate]
6) **Add over-header blocks** — Install seven 11-7/8" blocks at 16" OC starting above the left jack, running to the right jack, sitting on the cap up to the top plate. [Snapshot: header blocks]
7) **Set 6×80" studs to center the 72" opening** (all start at Z=1.5"):
   - Stud1 @ Y=1.5" (flush to left jack)
   - Stud2 @ Y=9.0" (+7.5")
   - Stud3 @ Y=10.5" (tight to stud2)
   - Stud4 @ Y=84.0" (+73.5" from stud3 → yields 72" clear gap)
   - Stud5 @ Y=85.5" (tight to stud4)
   - Stud6 @ Y=93.0" (against right jack)
   The clear face-to-face gap between Stud3 and Stud4 is 72", centered at the 48" midpoint. [Snapshot: studs placed]
8) **Top plate** — Install the 2x4x96 top plate aligned with the bottom plate; tie into kings/blocks. [Snapshot: finished frame]

## Usage (macro)
Set FreeCAD macro path to `FreeCAD/lumber`, open a new document, run `Sliding_Door_72x80.FCMacro`, and export snapshots at each step above to include in this guide.***
