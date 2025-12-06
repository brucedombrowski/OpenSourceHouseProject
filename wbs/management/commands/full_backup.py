import subprocess
from datetime import datetime
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Export full WBS backup (WBS + dependencies + timestamp) and zip it"

    def handle(self, *args, **options):
        root = Path.cwd()
        backup_dir = root / "backup"
        backup_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

        wbs_csv = backup_dir / "wbs_items.csv"
        dep_csv = backup_dir / "dependencies.csv"
        ts_file = backup_dir / "backup_timestamp.txt"
        zip_name = root / f"wbs_backup_{timestamp}.zip"

        # Write timestamp
        ts_file.write_text(timestamp)

        self.stdout.write("Exporting WBS...")
        self._run_cmd(["python", "manage.py", "export_wbs_csv", str(wbs_csv)])

        self.stdout.write("Exporting Dependencies...")
        self._run_cmd(["python", "manage.py", "export_dependencies_csv", str(dep_csv)])

        # Build zip archive
        self.stdout.write("Creating ZIP archive...")
        self._run_cmd(
            ["zip", "-r", str(zip_name), "backup"],
            check_exists=["zip"],
        )

        self.stdout.write(
            self.style.SUCCESS(f"\n✅ FULL BACKUP COMPLETE\nArchive created:\n{zip_name}\n")
        )

    def _run_cmd(self, cmd, check_exists=None):
        if check_exists:
            for binary in check_exists:
                if not self._binary_exists(binary):
                    raise CommandError(
                        f"Required system tool '{binary}' was not found.\n"
                        f"Install it or run manually without ZIP."
                    )
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise CommandError(result.stderr.strip())
        if result.stdout:
            self.stdout.write(result.stdout.strip())

    def _binary_exists(self, name):
        from shutil import which

        return which(name) is not None
