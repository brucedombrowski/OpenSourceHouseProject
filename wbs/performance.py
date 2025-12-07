# wbs/performance.py
"""
Performance profiling utilities for views and functions.

Provides decorators for timing view execution and query counting.
Use in development to identify slow views and N+1 query patterns.
"""

import functools
import logging
import time
from typing import Callable

from django.db import connection, reset_queries
from django.test.utils import CaptureQueriesContext

logger = logging.getLogger(__name__)


def profile_view(name: str = None) -> Callable:
    """
    Decorator to profile view execution time and query count.

    Usage:
        @profile_view("my_expensive_view")
        def my_view(request):
            ...

    Args:
        name: Optional name for the profile log (defaults to function name)

    Returns:
        Decorated function with timing and query profiling
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            profile_name = name or func.__name__

            # Reset queries to get accurate count
            if not hasattr(connection, "queries_log"):
                reset_queries()

            start_time = time.time()
            queries_before = len(connection.queries)

            result = func(*args, **kwargs)

            queries_after = len(connection.queries)
            elapsed_time = time.time() - start_time
            query_count = queries_after - queries_before

            # Log profiling info
            log_msg = (
                f"[PROFILE] {profile_name}: " f"{elapsed_time:.3f}s, " f"{query_count} queries"
            )

            if elapsed_time > 1.0:
                logger.warning(log_msg)
            else:
                logger.info(log_msg)

            return result

        return wrapper

    return decorator


def query_counter(func: Callable = None) -> Callable:
    """
    Decorator to count and log all database queries executed by a function.

    Usage:
        @query_counter
        def expensive_operation():
            ...

    Returns:
        Decorated function with query counting and logging
    """

    def decorator(fn: Callable) -> Callable:
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            # Capture all queries executed in this function
            with CaptureQueriesContext(connection) as ctx:
                result = fn(*args, **kwargs)
                query_count = len(ctx.captured_queries)

                # Log queries
                if query_count > 0:
                    logger.debug(f"[QUERIES] {fn.__name__} executed {query_count} queries")

                    # Log individual queries if in debug mode
                    for i, query in enumerate(ctx.captured_queries, 1):
                        logger.debug(f"  Query {i}: {query['sql'][:100]}...")

            return result

        return wrapper

    return decorator if func is None else decorator(func)


def log_query_details(func: Callable = None) -> Callable:
    """
    Decorator to log detailed query information (SQL, time, rows).

    Usage:
        @log_query_details
        def my_function():
            ...

    Returns:
        Decorated function with detailed query logging
    """

    def decorator(fn: Callable) -> Callable:
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            with CaptureQueriesContext(connection) as ctx:
                result = fn(*args, **kwargs)

                total_time = sum(float(q.get("time", 0)) for q in ctx.captured_queries)

                logger.info(
                    f"[QUERY DETAILS] {fn.__name__}: "
                    f"{len(ctx.captured_queries)} queries, "
                    f"{total_time:.4f}s total"
                )

                for i, query in enumerate(ctx.captured_queries, 1):
                    sql = query["sql"]
                    query_time = query.get("time", 0)
                    logger.info(f"  [{i}] {query_time:.4f}s: {sql[:150]}...")

            return result

        return wrapper

    return decorator if func is None else decorator(func)
