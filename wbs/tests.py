from datetime import date
from decimal import Decimal

from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model

from .models import ProjectItem, TaskDependency, WbsItem


class RollupTests(TestCase):
    """Test suite for WbsItem rollup functionality (dates and progress)."""

    def test_update_rollup_dates_rolls_up_from_descendants(self):
        """
        Root inherits min planned_start and max planned_end from descendants.
        """
        root = WbsItem.objects.create(code="1", name="Root")
        child = WbsItem.objects.create(code="1.1", name="Child", parent=root)
        WbsItem.objects.create(
            code="1.1.1",
            name="Grandchild",
            parent=child,
            planned_start=date(2025, 1, 1),
            planned_end=date(2025, 1, 3),
        )
        WbsItem.objects.create(
            code="1.2",
            name="Sibling",
            parent=root,
            planned_start=date(2025, 1, 10),
            planned_end=date(2025, 1, 12),
        )

        changed = root.update_rollup_dates(include_self=True)
        root.refresh_from_db()
        child.refresh_from_db()

        self.assertTrue(changed)
        self.assertEqual(child.planned_start, date(2025, 1, 1))
        self.assertEqual(child.planned_end, date(2025, 1, 3))
        self.assertEqual(root.planned_start, date(2025, 1, 1))
        self.assertEqual(root.planned_end, date(2025, 1, 12))

    def test_update_rollup_dates_returns_false_without_children(self):
        """
        Leaf node rollup should return False if include_self=False.
        """
        leaf = WbsItem.objects.create(
            code="1",
            name="Leaf",
            planned_start=date(2025, 1, 1),
            planned_end=date(2025, 1, 5),
        )
        changed = leaf.update_rollup_dates(include_self=False)
        self.assertFalse(changed)

    def test_update_rollup_dates_no_change_returns_false(self):
        """
        Rollup should return False if dates haven't changed.
        """
        root = WbsItem.objects.create(
            code="1",
            name="Root",
            planned_start=date(2025, 1, 1),
            planned_end=date(2025, 1, 5),
            duration_days=Decimal("5.00"),
        )
        WbsItem.objects.create(
            code="1.1",
            name="Child",
            parent=root,
            planned_start=date(2025, 1, 1),
            planned_end=date(2025, 1, 5),
        )

        changed = root.update_rollup_dates(include_self=True)
        self.assertFalse(changed)

    def test_update_rollup_dates_with_partial_dates(self):
        """
        Rollup should handle nodes with only start or only end dates.
        """
        root = WbsItem.objects.create(code="1", name="Root")
        WbsItem.objects.create(
            code="1.1",
            name="Only start",
            parent=root,
            planned_start=date(2025, 1, 1),
            planned_end=None,
        )
        WbsItem.objects.create(
            code="1.2",
            name="Only end",
            parent=root,
            planned_start=None,
            planned_end=date(2025, 1, 10),
        )

        root.update_rollup_dates(include_self=True)
        root.refresh_from_db()

        self.assertEqual(root.planned_start, date(2025, 1, 1))
        self.assertEqual(root.planned_end, date(2025, 1, 10))

    def test_update_rollup_progress_weights_by_duration(self):
        """
        Progress rollup should weight by duration_days.
        """
        root = WbsItem.objects.create(code="1", name="Root")
        WbsItem.objects.create(
            code="1.1",
            name="Short task",
            parent=root,
            duration_days=Decimal("2"),
            percent_complete=Decimal("25"),
        )
        WbsItem.objects.create(
            code="1.2",
            name="No duration defaults to weight 1",
            parent=root,
            duration_days=None,
            percent_complete=Decimal("75"),
        )

        changed = root.update_rollup_progress(include_self=True)
        root.refresh_from_db()

        self.assertTrue(changed)
        # Calculation: (25 * 2 + 75 * 1) / (2 + 1) = 125 / 3 = 41.67
        self.assertEqual(root.percent_complete, Decimal("41.67"))

    def test_update_rollup_progress_equal_weights(self):
        """
        When children have equal durations, progress should be average.
        """
        root = WbsItem.objects.create(code="1", name="Root")
        WbsItem.objects.create(
            code="1.1",
            name="Task 1",
            parent=root,
            duration_days=Decimal("5"),
            percent_complete=Decimal("50"),
        )
        WbsItem.objects.create(
            code="1.2",
            name="Task 2",
            parent=root,
            duration_days=Decimal("5"),
            percent_complete=Decimal("100"),
        )

        root.update_rollup_progress(include_self=True)
        root.refresh_from_db()

        self.assertEqual(root.percent_complete, Decimal("75.00"))

    def test_update_rollup_progress_zero_duration_default_weight(self):
        """
        Zero duration should default to weight 1, not cause division errors.
        """
        root = WbsItem.objects.create(code="1", name="Root")
        WbsItem.objects.create(
            code="1.1",
            name="Zero duration",
            parent=root,
            duration_days=Decimal("0"),
            percent_complete=Decimal("50"),
        )

        root.update_rollup_progress(include_self=True)
        root.refresh_from_db()

        self.assertEqual(root.percent_complete, Decimal("50.00"))

    def test_update_rollup_progress_leaf_unchanged(self):
        """
        Leaf nodes should keep their own percent_complete unchanged.
        """
        leaf = WbsItem.objects.create(
            code="1",
            name="Leaf",
            percent_complete=Decimal("42.50"),
        )

        changed = leaf.update_rollup_progress(include_self=True)
        leaf.refresh_from_db()

        self.assertFalse(changed)
        self.assertEqual(leaf.percent_complete, Decimal("42.50"))

    def test_update_rollup_recursive_depth(self):
        """
        Rollup should work across deep hierarchies (3+ levels).
        """
        root = WbsItem.objects.create(code="1", name="Root")
        mid = WbsItem.objects.create(code="1.1", name="Mid", parent=root)
        WbsItem.objects.create(
            code="1.1.1",
            name="Leaf",
            parent=mid,
            planned_start=date(2025, 1, 1),
            planned_end=date(2025, 1, 5),
            percent_complete=Decimal("50"),
        )

        root.update_rollup_dates(include_self=True)
        root.update_rollup_progress(include_self=True)

        root.refresh_from_db()
        mid.refresh_from_db()

        self.assertEqual(root.planned_start, date(2025, 1, 1))
        self.assertEqual(root.planned_end, date(2025, 1, 5))
        self.assertEqual(root.percent_complete, Decimal("50.00"))


class DependencyTests(TestCase):
    """Test suite for TaskDependency model and constraints."""

    def test_task_dependency_unique_together_constraint(self):
        """
        Creating duplicate predecessor->successor links should raise IntegrityError.
        """
        pred = WbsItem.objects.create(code="1", name="Predecessor")
        succ = WbsItem.objects.create(code="2", name="Successor")
        TaskDependency.objects.create(predecessor=pred, successor=succ)

        with transaction.atomic(), self.assertRaises(IntegrityError):
            TaskDependency.objects.create(predecessor=pred, successor=succ)

    def test_task_dependency_allows_reverse_direction(self):
        """
        Should allow both A->B and B->A (they're directional).
        """
        item_a = WbsItem.objects.create(code="1", name="Item A")
        item_b = WbsItem.objects.create(code="2", name="Item B")

        dep1 = TaskDependency.objects.create(
            predecessor=item_a,
            successor=item_b,
            dependency_type=TaskDependency.FS,
        )
        dep2 = TaskDependency.objects.create(
            predecessor=item_b,
            successor=item_a,
            dependency_type=TaskDependency.FS,
        )

        self.assertIsNotNone(dep1.id)
        self.assertIsNotNone(dep2.id)

    def test_task_dependency_all_types(self):
        """
        All four dependency types should be storable.
        """
        pred = WbsItem.objects.create(code="1", name="Predecessor")
        types = [TaskDependency.FS, TaskDependency.SS, TaskDependency.FF, TaskDependency.SF]

        for i, dep_type in enumerate(types):
            succ = WbsItem.objects.create(code=f"{i+2}", name=f"Successor {i+2}")
            dep = TaskDependency.objects.create(
                predecessor=pred,
                successor=succ,
                dependency_type=dep_type,
            )
            self.assertEqual(dep.dependency_type, dep_type)

    def test_task_dependency_with_lag(self):
        """
        Dependencies should support positive and negative lag (lead).
        """
        pred = WbsItem.objects.create(code="1", name="Predecessor")
        succ = WbsItem.objects.create(code="2", name="Successor")

        lag_pos = TaskDependency.objects.create(
            predecessor=pred,
            successor=succ,
            lag_days=Decimal("2.5"),
        )
        self.assertEqual(lag_pos.lag_days, Decimal("2.5"))

        # Create another successor for lead test
        succ2 = WbsItem.objects.create(code="3", name="Successor 2")
        lag_neg = TaskDependency.objects.create(
            predecessor=pred,
            successor=succ2,
            lag_days=Decimal("-1.0"),
        )
        self.assertEqual(lag_neg.lag_days, Decimal("-1.0"))

    def test_task_dependency_string_representation(self):
        """
        __str__ method should format cleanly: "pred_code → succ_code (type, lag_days)d"
        """
        pred = WbsItem.objects.create(code="1.1", name="Pred")
        succ = WbsItem.objects.create(code="1.2", name="Succ")
        dep = TaskDependency.objects.create(
            predecessor=pred,
            successor=succ,
            dependency_type=TaskDependency.FS,
            lag_days=Decimal("3"),
        )

        expected = "1.1 → 1.2 (FS, 3d)"
        self.assertEqual(str(dep), expected)

    def test_related_names_work(self):
        """
        Related names successor_links and predecessor_links should work.
        """
        pred = WbsItem.objects.create(code="1", name="Predecessor")
        succ1 = WbsItem.objects.create(code="2", name="Successor 1")
        succ2 = WbsItem.objects.create(code="3", name="Successor 2")

        TaskDependency.objects.create(predecessor=pred, successor=succ1)
        TaskDependency.objects.create(predecessor=pred, successor=succ2)

        self.assertEqual(pred.successor_links.count(), 2)
        self.assertEqual(succ1.predecessor_links.count(), 1)


class KanbanViewTests(TestCase):
    """Test suite for project item Kanban view."""

    def test_board_renders_and_groups_by_status(self):
        """
        Kanban board should render and group items by status.
        """
        root = WbsItem.objects.create(code="1", name="Root")
        ProjectItem.objects.create(
            title="Todo item",
            status=ProjectItem.STATUS_TODO,
            priority=ProjectItem.PRIORITY_HIGH,
            wbs_item=root,
        )
        ProjectItem.objects.create(
            title="In progress item",
            status=ProjectItem.STATUS_IN_PROGRESS,
            priority=ProjectItem.PRIORITY_MEDIUM,
        )

        resp = self.client.get(reverse("project_item_board"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Todo item")
        self.assertContains(resp, "In progress item")

    def test_status_update_endpoint_moves_item(self):
        """
        Status update endpoint should change ProjectItem status.
        """
        item = ProjectItem.objects.create(
            title="Move me",
            status=ProjectItem.STATUS_TODO,
            priority=ProjectItem.PRIORITY_LOW,
        )
        resp = self.client.post(
            reverse("project_item_status_update"),
            {"id": item.id, "status": ProjectItem.STATUS_DONE},
        )
        self.assertEqual(resp.status_code, 200)
        item.refresh_from_db()
        self.assertEqual(item.status, ProjectItem.STATUS_DONE)

    def test_status_update_validates_status(self):
        """
        Invalid status should return error.
        """
        item = ProjectItem.objects.create(
            title="Test",
            status=ProjectItem.STATUS_TODO,
        )
        resp = self.client.post(
            reverse("project_item_status_update"),
            {"id": item.id, "status": "invalid_status"},
        )
        self.assertEqual(resp.status_code, 400)
        data = resp.json()
        self.assertFalse(data["ok"])


class ListViewTests(TestCase):
    """Test suite for project item list view."""

    def test_list_view_renders(self):
        """
        List view should render successfully.
        """
        resp = self.client.get(reverse("project_item_list"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "List View")

    def test_list_view_groups_by_wbs(self):
        """
        List view should group items by linked WBS item.
        """
        root1 = WbsItem.objects.create(code="1", name="Project 1")
        root2 = WbsItem.objects.create(code="2", name="Project 2")

        ProjectItem.objects.create(
            title="Item for Project 1",
            status=ProjectItem.STATUS_TODO,
            wbs_item=root1,
        )
        ProjectItem.objects.create(
            title="Item for Project 2",
            status=ProjectItem.STATUS_TODO,
            wbs_item=root2,
        )
        ProjectItem.objects.create(
            title="Unlinked item",
            status=ProjectItem.STATUS_TODO,
            wbs_item=None,
        )

        resp = self.client.get(reverse("project_item_list"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Project 1")
        self.assertContains(resp, "Project 2")

    def test_list_view_search_filter(self):
        """
        List view search should find items by title, description, owner.
        """
        ProjectItem.objects.create(
            title="Alpha item",
            description="Contains beta",
            status=ProjectItem.STATUS_TODO,
        )
        ProjectItem.objects.create(
            title="Gamma item",
            status=ProjectItem.STATUS_TODO,
        )

        resp = self.client.get(reverse("project_item_list"), {"q": "beta"})
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Alpha item")
        self.assertNotContains(resp, "Gamma item")

    def test_list_view_type_filter(self):
        """
        Type filter should only show items of selected type.
        """
        ProjectItem.objects.create(
            title="A task",
            type=ProjectItem.TYPE_TASK,
            status=ProjectItem.STATUS_TODO,
        )
        ProjectItem.objects.create(
            title="An issue",
            type=ProjectItem.TYPE_ISSUE,
            status=ProjectItem.STATUS_TODO,
        )

        resp = self.client.get(
            reverse("project_item_list"),
            {"type": ProjectItem.TYPE_TASK},
        )
        self.assertContains(resp, "A task")
        self.assertNotContains(resp, "An issue")

    def test_list_view_status_filter(self):
        """
        Status filter should only show items with selected status.
        """
        ProjectItem.objects.create(
            title="Todo item",
            status=ProjectItem.STATUS_TODO,
        )
        ProjectItem.objects.create(
            title="Done item",
            status=ProjectItem.STATUS_DONE,
        )

        resp = self.client.get(
            reverse("project_item_list"),
            {"status": ProjectItem.STATUS_TODO},
        )
        self.assertContains(resp, "Todo item")
        self.assertNotContains(resp, "Done item")

    def test_list_view_priority_filter(self):
        """
        Priority filter should work correctly.
        """
        ProjectItem.objects.create(
            title="High priority",
            priority=ProjectItem.PRIORITY_HIGH,
            status=ProjectItem.STATUS_TODO,
        )
        ProjectItem.objects.create(
            title="Low priority",
            priority=ProjectItem.PRIORITY_LOW,
            status=ProjectItem.STATUS_TODO,
        )

        resp = self.client.get(
            reverse("project_item_list"),
            {"priority": ProjectItem.PRIORITY_HIGH},
        )
        self.assertContains(resp, "High priority")
        self.assertNotContains(resp, "Low priority")


class GanttShiftTests(TestCase):
    """Test suite for Gantt drag/shift scheduling."""

    def setUp(self):
        User = get_user_model()
        self.staff = User.objects.create_user(
            username="staff", password="pass", is_staff=True
        )
        self.client.force_login(self.staff)

    def test_shift_task_moves_children(self):
        """
        Shifting a parent should move all children by the same offset.
        """
        parent = WbsItem.objects.create(
            code="1",
            name="Parent",
            planned_start=date(2025, 1, 1),
            planned_end=date(2025, 1, 5),
        )
        child = WbsItem.objects.create(
            code="1.1",
            name="Child",
            parent=parent,
            planned_start=date(2025, 1, 2),
            planned_end=date(2025, 1, 4),
        )

        resp = self.client.post(
            reverse("gantt_shift_task"),
            {"code": parent.code, "new_start": "2025-01-06"},
        )
        self.assertEqual(resp.status_code, 200)

        parent.refresh_from_db()
        child.refresh_from_db()
        self.assertEqual(parent.planned_start, date(2025, 1, 6))
        self.assertEqual(parent.planned_end, date(2025, 1, 10))
        self.assertEqual(child.planned_start, date(2025, 1, 7))
        self.assertEqual(child.planned_end, date(2025, 1, 9))

