from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.db import transaction

from AssignEaseApp.models import Assignment, Class, Profile


class Command(BaseCommand):
    help = (
        "Fix Class.teacher and Assignment.teacher rows where a Profile.id was "
        "stored instead of the related auth_user.id. For assignments, the class "
        "owner is treated as the source of truth."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Persist the fixes. Without this flag the command runs in dry-run mode.",
        )

    def _resolved_teacher_id(self, stored_teacher_id):
        if not stored_teacher_id:
            return None

        current_user = User.objects.filter(id=stored_teacher_id).first()
        if current_user:
            current_profile = Profile.objects.filter(user=current_user).first()
            if current_profile and current_profile.role == "teacher":
                return stored_teacher_id

        mapped_profile = Profile.objects.filter(id=stored_teacher_id, role="teacher").first()
        if mapped_profile:
            return mapped_profile.user_id

        return None

    def _collect_class_fixes(self, queryset):
        fixes = []
        for obj in queryset.select_related("teacher"):
            new_teacher_id = self._resolved_teacher_id(obj.teacher_id)
            if new_teacher_id and new_teacher_id != obj.teacher_id:
                fixes.append((obj, obj.teacher_id, new_teacher_id))
                self.stdout.write(
                    f"[Class] id={obj.id}: teacher_id {obj.teacher_id} -> {new_teacher_id}"
                )
        return fixes

    def _collect_assignment_fixes(self, queryset):
        fixes = []
        for obj in queryset.select_related("teacher", "class_assigned", "class_assigned__teacher"):
            class_teacher_id = getattr(obj.class_assigned, "teacher_id", None)
            resolved_teacher_id = self._resolved_teacher_id(obj.teacher_id)
            new_teacher_id = None

            if class_teacher_id and obj.teacher_id != class_teacher_id:
                new_teacher_id = class_teacher_id
            elif resolved_teacher_id and resolved_teacher_id != obj.teacher_id:
                new_teacher_id = resolved_teacher_id

            if new_teacher_id and new_teacher_id != obj.teacher_id:
                fixes.append((obj, obj.teacher_id, new_teacher_id))
                self.stdout.write(
                    f"[Assignment] id={obj.id}: teacher_id {obj.teacher_id} -> {new_teacher_id} "
                    f"(class_id={obj.class_assigned_id})"
                )

        return fixes

    @transaction.atomic
    def handle(self, *args, **options):
        apply_changes = options["apply"]

        class_fixes = self._collect_class_fixes(Class.objects.all())
        assignment_fixes = self._collect_assignment_fixes(Assignment.objects.all())

        total_fixes = len(class_fixes) + len(assignment_fixes)
        if total_fixes == 0:
            self.stdout.write(self.style.SUCCESS("No mismatched teacher foreign keys found."))
            return

        self.stdout.write("")
        self.stdout.write(f"Detected {len(class_fixes)} class fix(es) and {len(assignment_fixes)} assignment fix(es).")

        if not apply_changes:
            self.stdout.write(
                self.style.WARNING(
                    "Dry run only. Re-run with `--apply` to save these changes."
                )
            )
            transaction.set_rollback(True)
            return

        for obj, _, new_teacher_id in class_fixes:
            obj.teacher_id = new_teacher_id
            obj.save(update_fields=["teacher"])

        for obj, _, new_teacher_id in assignment_fixes:
            obj.teacher_id = new_teacher_id
            obj.save(update_fields=["teacher"])

        self.stdout.write(self.style.SUCCESS(f"Applied {total_fixes} teacher foreign key fix(es)."))
