import time

from house_wbs.__version__ import __version__, __version_full__

# Compute once per process to avoid regenerating per request
_BUILD_TS = int(time.time())


def build_timestamp(_request):
    """Provide a stable build timestamp for cache-busting static assets."""
    return {
        "build_timestamp": _BUILD_TS,
        "app_version": __version__,
        "app_version_full": __version_full__,
    }
