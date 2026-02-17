from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Submission, AIEvaluation, Assignment
from .ai_worker import run_ai_background
from .email_service import EmailService
import logging

logger = logging.getLogger(__name__)

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
            ai = AIEvaluation.objects.create(
                submission=instance,
                assignment=instance.assignment,
                question=instance.question,
                student=instance.student,
                question_text=instance.question.title,
                student_answer=instance.code or instance.text_submission or ""
            )
            run_ai_background(ai.id)
            logger.info(f"AI evaluation created for submission {instance.id}")
        except Exception as e:
            logger.error(f"Failed to create AI evaluation: {str(e)}")


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
