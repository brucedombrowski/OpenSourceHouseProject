import time

# Compute once per process to avoid regenerating per request
_BUILD_TS = int(time.time())


def build_timestamp(_request):
    """Provide a stable build timestamp for cache-busting static assets."""
    return {"build_timestamp": _BUILD_TS}
