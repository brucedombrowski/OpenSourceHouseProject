# Generated migration for adding database indexes on frequently-queried fields

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("wbs", "0013_projectitem_owner_fk"),
    ]

    operations = [
        # ProjectItem indexes - for status/type filtering and board views
        migrations.AddIndex(
            model_name="projectitem",
            index=models.Index(fields=["status"], name="wbs_projectitem_status_idx"),
        ),
        migrations.AddIndex(
            model_name="projectitem",
            index=models.Index(fields=["type"], name="wbs_projectitem_type_idx"),
        ),
        migrations.AddIndex(
            model_name="projectitem",
            index=models.Index(fields=["priority"], name="wbs_projectitem_priority_idx"),
        ),
        migrations.AddIndex(
            model_name="projectitem",
            index=models.Index(fields=["wbs_item_id"], name="wbs_projectitem_wbs_item_idx"),
        ),
        migrations.AddIndex(
            model_name="projectitem",
            index=models.Index(
                fields=["status", "type"],
                name="wbs_projectitem_status_type_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="projectitem",
            index=models.Index(
                fields=["created_at"],
                name="wbs_projectitem_created_idx",
            ),
        ),
        # TaskDependency indexes - for circular dependency checks and dependency graphs
        migrations.AddIndex(
            model_name="taskdependency",
            index=models.Index(
                fields=["predecessor_id"],
                name="wbs_taskdep_predecessor_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="taskdependency",
            index=models.Index(
                fields=["successor_id"],
                name="wbs_taskdep_successor_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="taskdependency",
            index=models.Index(
                fields=["predecessor_id", "successor_id"],
                name="wbs_taskdep_pred_succ_idx",
            ),
        ),
        # WbsItem indexes - for tree navigation and status filtering
        migrations.AddIndex(
            model_name="wbsitem",
            index=models.Index(
                fields=["status"],
                name="wbs_wbsitem_status_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="wbsitem",
            index=models.Index(
                fields=["code"],
                name="wbs_wbsitem_code_idx",
            ),
        ),
        # Tag index for lookups
        migrations.AddIndex(
            model_name="tag",
            index=models.Index(
                fields=["name"],
                name="wbs_tag_name_idx",
            ),
        ),
    ]
