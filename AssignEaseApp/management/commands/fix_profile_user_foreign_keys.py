from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.db import IntegrityError, transaction

from AssignEaseApp.models import (
    AIEvaluation,
    Assignment,
    Class,
    ClassStudent,
    DatabaseSubmission,
    NonCodingSubmission,
    Profile,
    Submission,
    TeacherFeedback,
)


class Command(BaseCommand):
    help = (
        "Repair legacy foreign keys where Profile.id was stored in place of "
        "auth_user.id across teacher- and student-linked tables."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Persist the fixes. Without this flag the command runs in dry-run mode.",
        )

    def _resolve_user_id(self, stored_user_id, expected_role=None):
        if not stored_user_id:
            return None

        current_user = User.objects.filter(id=stored_user_id).first()
        current_profile = Profile.objects.filter(user=current_user).first() if current_user else None
        if current_user and (expected_role is None or (current_profile and current_profile.role == expected_role)):
            return stored_user_id

        mapped_profile = Profile.objects.filter(id=stored_user_id).first()
        if mapped_profile and (expected_role is None or mapped_profile.role == expected_role):
            return mapped_profile.user_id

        return None

    def _collect_class_fixes(self):
        fixes = []
        for obj in Class.objects.all():
            new_user_id = self._resolve_user_id(obj.teacher_id, "teacher")
            if new_user_id and new_user_id != obj.teacher_id:
                fixes.append((obj, "teacher_id", obj.teacher_id, new_user_id))
        return fixes

    def _collect_assignment_fixes(self):
        fixes = []
        for obj in Assignment.objects.select_related("class_assigned"):
            class_teacher_id = getattr(obj.class_assigned, "teacher_id", None)
            new_user_id = class_teacher_id or self._resolve_user_id(obj.teacher_id, "teacher")
            if new_user_id and new_user_id != obj.teacher_id:
                fixes.append((obj, "teacher_id", obj.teacher_id, new_user_id))
        return fixes

    def _collect_class_student_fixes(self):
        fixes = []
        for obj in ClassStudent.objects.all():
            new_user_id = self._resolve_user_id(obj.student_id, "student")
            if new_user_id and new_user_id != obj.student_id:
                fixes.append((obj, "student_id", obj.student_id, new_user_id))
        return fixes

    def _collect_submission_fixes(self):
        fixes = []
        for obj in Submission.objects.all():
            new_user_id = self._resolve_user_id(obj.student_id, "student")
            if new_user_id and new_user_id != obj.student_id:
                fixes.append((obj, "student_id", obj.student_id, new_user_id))
        return fixes

    def _collect_noncoding_submission_fixes(self):
        fixes = []
        for obj in NonCodingSubmission.objects.all():
            new_user_id = self._resolve_user_id(obj.student_id, "student")
            if new_user_id and new_user_id != obj.student_id:
                fixes.append((obj, "student_id", obj.student_id, new_user_id))
        return fixes

    def _collect_database_submission_fixes(self):
        fixes = []
        for obj in DatabaseSubmission.objects.all():
            new_user_id = self._resolve_user_id(obj.student_id, "student")
            if new_user_id and new_user_id != obj.student_id:
                fixes.append((obj, "student_id", obj.student_id, new_user_id))
        return fixes

    def _collect_ai_evaluation_fixes(self):
        fixes = []
        for obj in AIEvaluation.objects.select_related(
            "submission",
            "noncoding_submission",
            "database_submission",
        ):
            linked_student_id = (
                getattr(obj.submission, "student_id", None)
                or getattr(obj.noncoding_submission, "student_id", None)
                or getattr(obj.database_submission, "student_id", None)
            )
            new_user_id = linked_student_id or self._resolve_user_id(obj.student_id, "student")
            if new_user_id and new_user_id != obj.student_id:
                fixes.append((obj, "student_id", obj.student_id, new_user_id))
        return fixes

    def _collect_teacher_feedback_fixes(self):
        fixes = []
        for obj in TeacherFeedback.objects.select_related("submission__assignment"):
            linked_teacher_id = getattr(getattr(obj.submission, "assignment", None), "teacher_id", None)
            new_user_id = linked_teacher_id or self._resolve_user_id(obj.teacher_id, "teacher")
            if new_user_id and new_user_id != obj.teacher_id:
                fixes.append((obj, "teacher_id", obj.teacher_id, new_user_id))
        return fixes

    def _print_fixes(self, label, fixes):
        for obj, field_name, old_id, new_id in fixes:
            self.stdout.write(
                f"[{label}] id={obj.id}: {field_name} {old_id} -> {new_id}"
            )

    def _apply_fixes(self, label, fixes):
        applied = 0
        for obj, field_name, _, new_id in fixes:
            setattr(obj, field_name, new_id)
            try:
                obj.save(update_fields=[field_name[:-3] if field_name.endswith("_id") else field_name])
                applied += 1
            except IntegrityError as exc:
                self.stdout.write(
                    self.style.WARNING(
                        f"[{label}] id={obj.id} skipped due to integrity conflict: {exc}"
                    )
                )
        return applied

    @transaction.atomic
    def handle(self, *args, **options):
        apply_changes = options["apply"]

        fix_groups = [
            ("Class", self._collect_class_fixes()),
            ("Assignment", self._collect_assignment_fixes()),
            ("ClassStudent", self._collect_class_student_fixes()),
            ("Submission", self._collect_submission_fixes()),
            ("NonCodingSubmission", self._collect_noncoding_submission_fixes()),
            ("DatabaseSubmission", self._collect_database_submission_fixes()),
            ("AIEvaluation", self._collect_ai_evaluation_fixes()),
            ("TeacherFeedback", self._collect_teacher_feedback_fixes()),
        ]

        total = 0
        for label, fixes in fix_groups:
            if fixes:
                self._print_fixes(label, fixes)
                total += len(fixes)

        if total == 0:
            self.stdout.write(self.style.SUCCESS("No profile/user foreign key mismatches found."))
            return

        self.stdout.write("")
        self.stdout.write(f"Detected {total} fixable foreign key mismatch(es).")

        if not apply_changes:
            self.stdout.write(
                self.style.WARNING(
                    "Dry run only. Re-run with `--apply` to save these changes."
                )
            )
            transaction.set_rollback(True)
            return

        applied_total = 0
        for label, fixes in fix_groups:
            if fixes:
                applied_total += self._apply_fixes(label, fixes)

        self.stdout.write(self.style.SUCCESS(f"Applied {applied_total} foreign key fix(es)."))
