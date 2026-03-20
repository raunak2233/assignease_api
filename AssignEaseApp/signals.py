from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Submission, AIEvaluation, Assignment, DatabaseSubmission, NonCodingSubmission
from .ai_worker import run_ai_background
from .email_service import EmailService
import logging

logger = logging.getLogger(__name__)


def _build_noncoding_question_text(assignment):
    questions = list(assignment.non_coding_questions.all().order_by('order'))
    if questions:
        return "\n".join(
            [f"{index + 1}. {question.question_text}" for index, question in enumerate(questions)]
        )
    return assignment.title


def _build_noncoding_answer_text(instance):
    file_names = []
    try:
        file_names = [file.file.name.split('/')[-1] for file in instance.files.all()]
    except Exception:
        file_names = []

    answer_parts = []
    if instance.text_submission:
        answer_parts.append(instance.text_submission)
    if file_names:
        answer_parts.append("Uploaded files: " + ", ".join(file_names))

    return "\n".join(answer_parts).strip()


def _sync_ai_evaluation(*, lookup, assignment, student, question=None, question_text="", student_answer=""):
    ai, created = AIEvaluation.objects.get_or_create(
        **lookup,
        defaults={
            "assignment": assignment,
            "question": question,
            "student": student,
            "question_text": question_text,
            "student_answer": student_answer,
        },
    )

    should_rerun = created
    fields_to_update = []

    for field_name, new_value in (
        ("assignment", assignment),
        ("question", question),
        ("student", student),
        ("question_text", question_text),
        ("student_answer", student_answer),
    ):
        if getattr(ai, field_name) != new_value:
            setattr(ai, field_name, new_value)
            fields_to_update.append(field_name)
            should_rerun = True

    if should_rerun:
        ai.status = "pending"
        ai.error = None
        ai.ai_score = None
        ai.confidence = None
        ai.feedback = None
        ai.raw_response = None
        ai.mistake_type = None
        ai.completed_at = None
        fields_to_update.extend(
            [
                "status",
                "error",
                "ai_score",
                "confidence",
                "feedback",
                "raw_response",
                "mistake_type",
                "completed_at",
            ]
        )
        ai.save(update_fields=list(dict.fromkeys(fields_to_update)))
        run_ai_background(ai.id)

    return ai, should_rerun

# Signal for Assignment creation
@receiver(post_save, sender=Assignment)
def notify_on_assignment_creation(sender, instance, created, **kwargs):
    """Send notification emails when a new assignment is created"""
    if created:
        try:
            # Notify teacher
            EmailService.send_assignment_created_to_teacher(instance)
            logger.info(f"Assignment creation email sent to teacher for {instance.title}")
        except Exception as e:
            logger.error(f"Failed to send assignment creation email to teacher: {str(e)}")
        
        try:
            # Notify all students in the class
            EmailService.send_assignment_created_to_students(instance)
            logger.info(f"Assignment creation emails sent to students for {instance.title}")
        except Exception as e:
            logger.error(f"Failed to send assignment creation emails to students: {str(e)}")


# Signal for Submission creation
@receiver(post_save, sender=Submission)
def create_ai_eval_and_notify(sender, instance, created, **kwargs):
    """Create AI evaluation and send notification emails when submission is created"""
    if created:
        # Send submission confirmation to student
        try:
            EmailService.send_submission_confirmation(instance)
            logger.info(f"Submission confirmation email sent to {instance.student.username}")
        except Exception as e:
            logger.error(f"Failed to send submission confirmation email: {str(e)}")
        
        # Notify teacher about new submission
        try:
            EmailService.send_submission_for_review_to_teacher(instance)
            logger.info(f"Submission review notification sent to teacher")
        except Exception as e:
            logger.error(f"Failed to send submission review email to teacher: {str(e)}")
        
        # Create AI evaluation
        try:
            _, rerun = _sync_ai_evaluation(
                lookup={"submission": instance},
                assignment=instance.assignment,
                question=instance.question,
                student=instance.student,
                question_text=instance.question.title,
                student_answer=instance.code or instance.text_submission or "",
            )
            if rerun:
                logger.info(f"AI evaluation created for submission {instance.id}")
        except Exception as e:
            logger.error(f"Failed to create AI evaluation: {str(e)}")


@receiver(post_save, sender=DatabaseSubmission)
def create_ai_eval_for_database_submission(sender, instance, created, **kwargs):
    try:
        question_text = (
            f"{instance.question.question_text}\n\n"
            f"Teacher expected query:\n{instance.question.expected_query or 'N/A'}\n\n"
            f"Auto feedback:\n{instance.feedback or 'N/A'}"
        )
        _, rerun = _sync_ai_evaluation(
            lookup={"database_submission": instance},
            assignment=instance.assignment,
            student=instance.student,
            question=None,
            question_text=question_text,
            student_answer=instance.submitted_query or "",
        )
        if rerun:
            logger.info(f"AI evaluation synced for database submission {instance.id}")
    except Exception as e:
        logger.error(f"Failed to create AI evaluation for database submission: {str(e)}")


@receiver(post_save, sender=NonCodingSubmission)
def create_ai_eval_for_noncoding_submission(sender, instance, created, **kwargs):
    try:
        _, rerun = _sync_ai_evaluation(
            lookup={"noncoding_submission": instance},
            assignment=instance.assignment,
            student=instance.student,
            question=None,
            question_text=_build_noncoding_question_text(instance.assignment),
            student_answer=_build_noncoding_answer_text(instance),
        )
        if rerun:
            logger.info(f"AI evaluation synced for non-coding submission {instance.id}")
    except Exception as e:
        logger.error(f"Failed to create AI evaluation for non-coding submission: {str(e)}")


# Signal for AI Evaluation completion
@receiver(post_save, sender=AIEvaluation)
def notify_on_ai_evaluation_complete(sender, instance, created, update_fields, **kwargs):
    """Send notification emails when AI evaluation is complete"""
    # Check if status changed to 'done' (only send on completion, not creation)
    if not created and update_fields and ('status' in update_fields or update_fields is None):
        if instance.status == 'done':
            try:
                # Notify student
                EmailService.send_ai_evaluation_to_student(instance)
                logger.info(f"AI evaluation result email sent to {instance.student.username}")
            except Exception as e:
                logger.error(f"Failed to send AI evaluation email to student: {str(e)}")
            
            try:
                # Notify teacher
                EmailService.send_ai_evaluation_to_teacher(instance)
                logger.info(f"AI evaluation result email sent to teacher")
            except Exception as e:
                logger.error(f"Failed to send AI evaluation email to teacher: {str(e)}")
