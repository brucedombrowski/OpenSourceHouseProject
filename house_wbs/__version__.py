"""
Version information for the Open Source House Project.

This file tracks the semantic version of the application.
Update this before each release.

Semantic Versioning: MAJOR.MINOR.PATCH
- MAJOR: Breaking changes
- MINOR: New features, backwards compatible
- PATCH: Bug fixes, no new features
"""

__version__ = "1.0.0"
__version_info__ = (1, 0, 0)

# Release date (YYYY-MM-DD)
__release_date__ = "2025-12-09"

# Short version (e.g., "1.0")
__version_short__ = f"{__version_info__[0]}.{__version_info__[1]}"

# Full version string (e.g., "1.0.0 (2025-12-09)")
__version_full__ = f"{__version__} ({__release_date__})"
