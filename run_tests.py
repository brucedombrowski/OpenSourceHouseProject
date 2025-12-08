#!/usr/bin/env python
"""
Test runner for wbs application.

Runs tests sequentially by class to avoid database locking issues
that occur when all tests run in a single process.

Known issue: Running `python manage.py test wbs` hangs indefinitely.
This script works around that by running each test class separately.
"""

import subprocess
import sys

# Test classes in the wbs.tests module
TEST_CLASSES = [
    "wbs.tests.RollupTests",
    "wbs.tests.TaskDependencyTests",
    "wbs.tests.WbsModelTests",
    "wbs.tests.ProjectItemModelTests",
    "wbs.tests.ListViewPaginationTests",
    "wbs.tests.GanttDragTests",
    "wbs.tests.ProjectItemViewTests",
]


def run_tests(verbosity=1, test_pattern=None):
    """Run all test classes individually.

    Args:
        verbosity: Django test verbosity level (0, 1, or 2)
        test_pattern: Optional pattern to filter test classes (e.g. "Rollup")
    """

    total_passed = 0
    total_failed = 0
    failed_classes = []

    print("=" * 70)
    print("Running WBS Tests (Sequential Mode)")
    print("=" * 70)

    # Filter test classes if pattern provided
    classes_to_run = TEST_CLASSES
    if test_pattern:
        classes_to_run = [c for c in TEST_CLASSES if test_pattern.lower() in c.lower()]
        if not classes_to_run:
            print(f"No test classes match pattern: {test_pattern}")
            return 1

    for test_class in classes_to_run:
        class_name = test_class.split(".")[-1]
        print(f"\n[Running] {class_name}...", end=" ", flush=True)

        try:
            result = subprocess.run(
                [sys.executable, "manage.py", "test", test_class, "-v", str(verbosity)],
                capture_output=True,
                text=True,
                timeout=60,
            )

            if result.returncode == 0:
                # Extract test count from output
                output_lines = result.stdout.strip().split("\n")
                for line in output_lines:
                    if "Ran" in line and "test" in line:
                        print(f"✓ {line.strip()}")
                        # Extract number of tests
                        try:
                            num_tests = int(line.split()[1])
                            total_passed += num_tests
                        except (ValueError, IndexError):
                            pass
                        break
                else:
                    print("✓ OK")
                    total_passed += 1
            else:
                print("✗ FAILED")
                print(result.stdout)
                print(result.stderr)
                failed_classes.append(test_class)
                total_failed += 1

        except subprocess.TimeoutExpired:
            print("✗ TIMEOUT (60s)")
            failed_classes.append(test_class)
            total_failed += 1

        except Exception as e:
            print(f"✗ ERROR: {e}")
            failed_classes.append(test_class)
            total_failed += 1

    # Print summary
    print("\n" + "=" * 70)
    print(f"Results: {total_passed} passed, {total_failed} failed")
    if failed_classes:
        print("\nFailed classes:")
        for cls in failed_classes:
            print(f"  - {cls}")
    print("=" * 70)

    return 0 if total_failed == 0 else 1


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run WBS tests sequentially")
    parser.add_argument(
        "-v", "--verbosity", type=int, default=1, choices=[0, 1, 2], help="Test verbosity level"
    )
    parser.add_argument("-p", "--pattern", help="Filter test classes by pattern")
    args = parser.parse_args()

    sys.exit(run_tests(verbosity=args.verbosity, test_pattern=args.pattern))
