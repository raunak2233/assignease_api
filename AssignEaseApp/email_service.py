"""
Email service for sending formatted HTML emails to users
"""
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)


class EmailService:
    """Handles sending formatted HTML emails"""

    @staticmethod
    def send_email(
        subject: str,
        recipients: List[str],
        template_name: str,
        context: Dict,
        from_email: str = None
    ) -> bool:
        """
        Send an HTML email using Django templates
        
        Args:
            subject: Email subject line
            recipients: List of email addresses
            template_name: Path to template file (e.g., 'emails/assignment_created.html')
            context: Dictionary of context variables for template
            from_email: Sender email (defaults to settings.DEFAULT_FROM_EMAIL)
            
        Returns:
            bool: True if email sent successfully, False otherwise
        """
        try:
            if not from_email:
                from_email = settings.DEFAULT_FROM_EMAIL

            # Render HTML template
            html_content = render_to_string(template_name, context)
            text_content = strip_tags(html_content)

            # Create email
            email = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=from_email,
                to=recipients,
            )
            email.attach_alternative(html_content, "text/html")

            # Send email
            email.send(fail_silently=False)
            logger.info(f"Email '{subject}' sent to {recipients}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email '{subject}': {str(e)}")
            return False

    @staticmethod
    def send_assignment_created_to_teacher(assignment) -> bool:
        """Notify teacher that assignment has been created and is live"""
        subject = f"✅ Assignment Created: {assignment.title}"
        recipients = [assignment.teacher.email]
        
        # Get teacher's profile name
        teacher_name = assignment.teacher.profile.name if hasattr(assignment.teacher, 'profile') and assignment.teacher.profile.name else assignment.teacher.first_name or assignment.teacher.username
        
        context = {
            'teacher_name': teacher_name,
            'assignment_title': assignment.title,
            'class_name': assignment.class_assigned.class_name,
            'due_date': assignment.due_date,
            'description': assignment.description,
            'created_at': assignment.created_at,
            'base_url': settings.ALLOWED_HOSTS[0] if settings.ALLOWED_HOSTS else 'localhost',
        }
        
        return EmailService.send_email(
            subject=subject,
            recipients=recipients,
            template_name='emails/assignment_created_teacher.html',
            context=context
        )

    @staticmethod
    def send_assignment_created_to_students(assignment) -> bool:
        """Notify all students in the class about the new assignment"""
        from .models import ClassStudent
        
        # Get all students in the class
        class_students = ClassStudent.objects.filter(class_assigned=assignment.class_assigned)
        recipients = [student.student.email for student in class_students]
        
        if not recipients:
            logger.info(f"No students found in class {assignment.class_assigned.class_name}")
            return False

        subject = f"📚 New Assignment: {assignment.title}"
        
        # Get teacher's profile name
        teacher_name = assignment.teacher.profile.name if hasattr(assignment.teacher, 'profile') and assignment.teacher.profile.name else assignment.teacher.first_name or assignment.teacher.username
        
        context = {
            'assignment_title': assignment.title,
            'class_name': assignment.class_assigned.class_name,
            'due_date': assignment.due_date,
            'description': assignment.description,
            'teacher_name': teacher_name,
            'created_at': assignment.created_at,
            'base_url': settings.ALLOWED_HOSTS[0] if settings.ALLOWED_HOSTS else 'localhost',
        }
        
        return EmailService.send_email(
            subject=subject,
            recipients=recipients,
            template_name='emails/assignment_created_student.html',
            context=context
        )

    @staticmethod
    def send_student_registration_confirmation(user, role) -> bool:
        """Notify user about successful registration"""
        subject = "🎉 Welcome to AssignEase!"
        recipients = [user.email]
        
        # Get user's profile name
        user_name = user.profile.name if hasattr(user, 'profile') and user.profile.name else user.first_name or user.username
        
        context = {
            'username': user_name,
            'role': role.upper(),
            'registration_date': user.date_joined,
            'base_url': settings.ALLOWED_HOSTS[0] if settings.ALLOWED_HOSTS else 'localhost',
        }
        
        return EmailService.send_email(
            subject=subject,
            recipients=recipients,
            template_name='emails/user_registration.html',
            context=context
        )

    @staticmethod
    def send_submission_confirmation(submission) -> bool:
        """Notify student that their submission has been received"""
        subject = f"✅ Submission Received: {submission.assignment.title}"
        recipients = [submission.student.email]
        
        # Get student's profile name
        student_name = submission.student.profile.name if hasattr(submission.student, 'profile') and submission.student.profile.name else submission.student.first_name or submission.student.username
        
        context = {
            'student_name': student_name,
            'assignment_title': submission.assignment.title,
            'class_name': submission.assignment.class_assigned.class_name,
            'question_title': submission.question.title,
            'submitted_at': submission.submitted_at,
            'base_url': settings.ALLOWED_HOSTS[0] if settings.ALLOWED_HOSTS else 'localhost',
        }
        
        return EmailService.send_email(
            subject=subject,
            recipients=recipients,
            template_name='emails/submission_received.html',
            context=context
        )

    @staticmethod
    def send_ai_evaluation_to_student(ai_evaluation) -> bool:
        """Notify student about AI evaluation results"""
        submission = ai_evaluation.submission
        subject = f"🤖 AI Evaluation Complete: {submission.assignment.title}"
        recipients = [ai_evaluation.student.email]
        
        # Get student's profile name
        student_name = ai_evaluation.student.profile.name if hasattr(ai_evaluation.student, 'profile') and ai_evaluation.student.profile.name else ai_evaluation.student.first_name or ai_evaluation.student.username
        
        context = {
            'student_name': student_name,
            'assignment_title': submission.assignment.title,
            'question_title': ai_evaluation.question.title,
            'ai_score': ai_evaluation.ai_score,
            'confidence': ai_evaluation.confidence,
            'feedback': ai_evaluation.feedback,
            'mistake_type': ai_evaluation.mistake_type,
            'completed_at': ai_evaluation.completed_at,
            'base_url': settings.ALLOWED_HOSTS[0] if settings.ALLOWED_HOSTS else 'localhost',
        }
        
        return EmailService.send_email(
            subject=subject,
            recipients=recipients,
            template_name='emails/ai_evaluation_result.html',
            context=context
        )

    @staticmethod
    def send_ai_evaluation_to_teacher(ai_evaluation) -> bool:
        """Notify teacher about AI evaluation completion for a student submission"""
        submission = ai_evaluation.submission
        teacher = submission.assignment.teacher
        
        # Get teacher and student profile names
        teacher_name = teacher.profile.name if hasattr(teacher, 'profile') and teacher.profile.name else teacher.first_name or teacher.username
        student_name = submission.student.profile.name if hasattr(submission.student, 'profile') and submission.student.profile.name else submission.student.first_name or submission.student.username
        
        subject = f"📊 AI Evaluation Complete: {student_name} - {submission.assignment.title}"
        recipients = [teacher.email]
        
        context = {
            'teacher_name': teacher_name,
            'student_name': student_name,
            'assignment_title': submission.assignment.title,
            'question_title': ai_evaluation.question.title,
            'ai_score': ai_evaluation.ai_score,
            'confidence': ai_evaluation.confidence,
            'feedback': ai_evaluation.feedback,
            'mistake_type': ai_evaluation.mistake_type,
            'completed_at': ai_evaluation.completed_at,
            'base_url': settings.ALLOWED_HOSTS[0] if settings.ALLOWED_HOSTS else 'localhost',
        }
        
        return EmailService.send_email(
            subject=subject,
            recipients=recipients,
            template_name='emails/ai_evaluation_teacher.html',
            context=context
        )

    @staticmethod
    def send_submission_for_review_to_teacher(submission) -> bool:
        """Notify teacher about a new student submission"""
        teacher = submission.assignment.teacher
        
        # Get teacher and student profile names
        teacher_name = teacher.profile.name if hasattr(teacher, 'profile') and teacher.profile.name else teacher.first_name or teacher.username
        student_name = submission.student.profile.name if hasattr(submission.student, 'profile') and submission.student.profile.name else submission.student.first_name or submission.student.username
        
        subject = f"📤 New Submission: {student_name} - {submission.assignment.title}"
        recipients = [teacher.email]
        
        context = {
            'teacher_name': teacher_name,
            'student_name': student_name,
            'assignment_title': submission.assignment.title,
            'question_title': submission.question.title,
            'submitted_at': submission.submitted_at,
            'base_url': settings.ALLOWED_HOSTS[0] if settings.ALLOWED_HOSTS else 'localhost',
        }
        
        return EmailService.send_email(
            subject=subject,
            recipients=recipients,
            template_name='emails/submission_for_review_teacher.html',
            context=context
        )
