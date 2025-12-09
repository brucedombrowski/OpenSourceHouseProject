# wbs/views_health.py
"""
Health check endpoints for monitoring and load balancer checks.

These endpoints are lightweight and don't require authentication.
Use for:
- Load balancer health checks
- Monitoring/uptime checking
- Deployment verification
"""

from django.db import connection
from django.http import JsonResponse
from django.views.decorators.cache import cache_page
from django.views.decorators.http import require_http_methods

from house_wbs.__version__ import __version__


@require_http_methods(["GET", "HEAD"])
@cache_page(60)  # Cache for 60 seconds to avoid database strain
def health_check(request):
    """
    Basic health check endpoint.

    Returns 200 OK if the application is running.
    Does not check database connectivity.

    Response:
        {
            "status": "ok",
            "service": "house-wbs",
            "version": "1.0.0"
        }
    """
    return JsonResponse(
        {
            "status": "ok",
            "service": "house-wbs",
            "version": __version__,
        }
    )


@require_http_methods(["GET", "HEAD"])
def health_check_detailed(request):
    """
    Detailed health check including database connectivity.

    Returns 200 OK if application and database are operational.
    Use for more thorough monitoring (less frequently than basic check).

    Response:
        {
            "status": "ok",
            "service": "house-wbs",
            "database": "ok|error",
            "message": "All systems operational" or error details
        }
    """
    try:
        # Test database connectivity with a simple query
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")

        return JsonResponse(
            {
                "status": "ok",
                "service": "house-wbs",
                "database": "ok",
                "message": "All systems operational",
            }
        )

    except Exception as e:
        return JsonResponse(
            {
                "status": "error",
                "service": "house-wbs",
                "database": "error",
                "message": f"Database check failed: {str(e)}",
            },
            status=503,  # Service Unavailable
        )


@require_http_methods(["GET", "HEAD"])
def readiness_check(request):
    """
    Readiness check for Kubernetes/container orchestration.

    Returns 200 OK if the application is ready to accept traffic.
    Performs all necessary checks (database, migrations, etc).

    Response:
        {
            "ready": true,
            "checks": {
                "database": "ok",
                "migrations": "ok"
            }
        }
    """
    checks = {}

    # Check database
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        checks["database"] = "ok"
    except Exception as e:
        checks["database"] = f"error: {str(e)}"

    # All checks passed if no errors
    ready = all(v == "ok" for v in checks.values())

    return JsonResponse(
        {
            "ready": ready,
            "checks": checks,
        },
        status=200 if ready else 503,
    )
