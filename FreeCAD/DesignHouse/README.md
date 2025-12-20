# Beach House Design System

Parametric 3D CAD design system for building beach houses using FreeCAD.

For Luke Dombrowski. Stay Alive.

## Quick Start (ExampleBeachHouse)

To build the example beach house:

```bash
cd FreeCAD/DesignHouse/ExampleBeachHouse
./build.sh
```

This will:
- Generate a timestamped 3D model (`.fcstd` file)
- Create build snapshots (foundation, joists, stairs, etc.)
- Export a bill of materials (BOM) CSV
- Open the model in FreeCAD GUI for visual inspection

All outputs go to `ExampleBeachHouse/builds/`.

## Creating Your Own House

1. **Copy the template**:
   ```bash
   mkdir MyHouse
   cp config_template.py MyHouse/config.py
   cp ExampleBeachHouse/build.sh MyHouse/
   ```

2. **Edit your config**:
   ```bash
   # Edit MyHouse/config.py with your lot dimensions, setbacks, etc.
   vim MyHouse/config.py
   ```

3. **Build your house**:
   ```bash
   cd MyHouse
   ./build.sh
   ```

## Configuration

All house parameters live in `config.py`:

- **LOT**: Lot dimensions, setbacks, coordinate system
- **FOUNDATION**: Pile grid, spacing, beams, blocking
- **FIRST_FLOOR**: Joist modules, sheathing, hangers
- **WALLS**: Framing, plate stock, positioning
- **DECKS**: Front/rear deck dimensions and modules
- **STAIRS**: Exterior stairs (rise, run, width)
- **ELEVATOR**: Beach house elevator/lift (if needed)
- **UTILITIES**: Concrete slab, water, electrical, plumbing
- **SEPTIC_SYSTEM**: Tank and leach field positioning
- **BUILD**: What to include in the build

See `config_template.py` for full documentation of all parameters.

## Coordinate System

Origin at southwest corner of lot (0, 0, 0):
- **X axis**: Increases EAST (left → right when viewing from above)
- **Y axis**: Increases NORTH (front → rear, facing north)
- **Z axis**: Increases UP (grade → sky)

Centerlines:
- **EW Centerline**: X = lot_width_ft / 2 (runs north-south)
- **NS Centerline**: Y = lot_depth_ft / 2 (runs east-west)

## File Structure

```
FreeCAD/DesignHouse/
├── BeachHouse Template.FCMacro   # Main build orchestration
├── design_house.sh                # Generic build script
├── config_template.py             # Starter template for new houses
├── ExampleBeachHouse/             # Reference implementation
│   ├── config.py                  # Example house configuration
│   ├── build.sh                   # Convenience script
│   └── builds/                    # Build outputs
└── macros/                        # Shared helper modules
    ├── beach_common.py
    ├── beam_assemblies.py
    ├── septic_utilities.py
    ├── beach_elevator.py
    └── ...
```

## Design Principles

1. **Single Source of Truth**: All dimensions in config, no hardcoded values
2. **DRY (Don't Repeat Yourself)**: Reusable macros and helpers
3. **Corner-Snapping**: All geometry derived from actual component dimensions
4. **BOM Accuracy**: Every part tracked for material ordering
5. **Code as Construction Docs**: Clear, documented, buildable designs

## Environment Variables

- `BEACH_CONFIG`: Path to config file (set automatically by `build.sh`)
- `BUILD_DIR`: Output directory for builds (default: `./builds`)
- `NO_OPEN=1`: Skip opening FreeCAD GUI after build
- `SNAPSHOT=0`: Skip snapshot generation

## Advanced Usage

### Build without opening GUI:
```bash
NO_OPEN=1 ./build.sh
```

### Skip snapshots (faster builds):
```bash
SNAPSHOT=0 ./build.sh
```

### Custom build directory:
```bash
BUILD_DIR=/tmp/my_builds ./build.sh
```

## Documentation

- See `CODING_STANDARDS.md` for construction-grade code standards
- See `HARDCODED_VALUES_AUDIT.md` for refactoring guidelines
- Each helper module (`macros/*.py`) has inline documentation

## License

For Luke Dombrowski. Stay Alive.
