#!/usr/bin/env python
"""
Static assets build script.

Collects and optimizes CSS/JS files for production deployment.
- Gathers all static files from apps and project root
- Adds content hashes to filenames for cache busting
- Generates manifest.json for reliable asset loading

Usage:
    python build_assets.py      # Collect and process static files
    python build_assets.py --clean  # Clean build (remove old staticfiles/)
"""

import json
import os
import shutil
import sys
from pathlib import Path

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "house_wbs.settings")

import django  # noqa: E402
from django.conf import settings  # noqa: E402
from django.core.management import call_command  # noqa: E402

django.setup()


def build_assets(clean=False):
    """Collect and process static files."""
    static_root = Path(settings.STATIC_ROOT)

    print("Building static assets...")
    print(f"  Static root: {static_root}")

    # Clean old build if requested
    if clean and static_root.exists():
        print(f"  Removing old build: {static_root}")
        shutil.rmtree(static_root)

    # Create static root if it doesn't exist
    static_root.mkdir(parents=True, exist_ok=True)

    # Collect static files with manifest storage
    print("  Collecting static files...")
    try:
        call_command("collectstatic", "--noinput", "--clear", verbosity=1)
        print("✓ Static files collected successfully")

        # Report manifest file location
        manifest_path = static_root / "staticfiles.json"
        if manifest_path.exists():
            with open(manifest_path) as f:
                manifest = json.load(f)
            print(f"✓ Manifest created with {len(manifest.get('paths', {}))} files")
            print(f"  Manifest: {manifest_path}")
        else:
            print("  Note: staticfiles.json not found (may be disabled)")

    except Exception as e:
        print(f"✗ Error collecting static files: {e}")
        return False

    # Report statistics
    if static_root.exists():
        total_size = sum(f.stat().st_size for f in static_root.rglob("*") if f.is_file())
        total_size_mb = total_size / (1024 * 1024)
        print(f"✓ Total size: {total_size_mb:.2f} MB")

    print("\nBuild complete! Ready for deployment.")
    return True


if __name__ == "__main__":
    clean = "--clean" in sys.argv
    success = build_assets(clean=clean)
    sys.exit(0 if success else 1)
