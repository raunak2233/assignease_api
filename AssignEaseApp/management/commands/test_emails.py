"""
Management command to test email notifications
Usage: python manage.py test_emails [--full|--registration|--assignment|--submission|--ai]
"""

from django.core.management.base import BaseCommand
from django.core import mail
from django.contrib.auth.models import User
from AssignEaseApp.models import (
    Profile, Class, ClassStudent, Assignment, 
    AssignmentQuestion, Submission, AIEvaluation
)
from AssignEaseApp.email_service import EmailService
from datetime import datetime, timedelta


class Command(BaseCommand):
    help = 'Test the email notification system'

    def add_arguments(self, parser):
        parser.add_argument(
            '--type',
            type=str,
            default='full',
            help='Type of test: full, registration, assignment, submission, ai'
        )

    def handle(self, *args, **options):
        test_type = options.get('type', 'full')
        
        self.stdout.write(self.style.SUCCESS(
            '\n' + '=' * 70
        ))
        self.stdout.write(self.style.SUCCESS(
            'AssignEase Email System Test'
        ))
        self.stdout.write(self.style.SUCCESS(
            '=' * 70 + '\n'
        ))

        if test_type in ['full', 'registration']:
            self.test_registration()
        
        if test_type in ['full', 'assignment']:
            self.test_assignment()
        
        if test_type in ['full', 'submission']:
            self.test_submission()
        
        if test_type in ['full', 'ai']:
            self.test_ai_evaluation()

        self.print_summary()

    def test_registration(self):
        """Test user registration email"""
        self.stdout.write(self.style.WARNING(
            '\n[TEST 1] User Registration Email'
        ))
        self.stdout.write('-' * 70)
        
        try:
            # Check if user already exists
            if not User.objects.filter(username='test_register_user').exists():
                user = User.objects.create_user(
                    username='test_register_user',
                    email='register@test.example.com',
                    password='testpass123',
                    first_name='Register'
                )
                profile = Profile.objects.create(
                    user=user,
                    role='student',
                    name='Test Register User'
                )
            else:
                user = User.objects.get(username='test_register_user')
            
            self.stdout.write(self.style.SUCCESS(
                f'✓ User registration email test ready'
            ))
            self.stdout.write(f'  Username: {user.username}')
            self.stdout.write(f'  Email: {user.email}')
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ Error: {str(e)}'))

    def test_assignment(self):
        """Test assignment creation emails"""
        self.stdout.write(self.style.WARNING(
            '\n[TEST 2] Assignment Creation Emails'
        ))
        self.stdout.write('-' * 70)
        
        try:
            # Get or create teacher
            teacher, _ = User.objects.get_or_create(
                username='test_teacher_email',
                defaults={
                    'email': 'teacher@test.example.com',
                    'first_name': 'Teacher'
                }
            )
            
            # Ensure teacher profile exists
            Profile.objects.get_or_create(
                user=teacher,
                defaults={'role': 'teacher', 'name': 'Test Teacher'}
            )
            
            # Get or create class
            test_class, _ = Class.objects.get_or_create(
                class_name='Test Class for Email',
                teacher=teacher
            )
            
            # Get or create student
            student, _ = User.objects.get_or_create(
                username='test_student_email',
                defaults={
                    'email': 'student@test.example.com',
                    'first_name': 'Student'
                }
            )
            
            Profile.objects.get_or_create(
                user=student,
                defaults={'role': 'student', 'name': 'Test Student'}
            )
            
            # Enroll student in class
            ClassStudent.objects.get_or_create(
                student=student,
                class_assigned=test_class
            )
            
            # Create assignment
            if not Assignment.objects.filter(
                title='Test Assignment for Email',
                teacher=teacher
            ).exists():
                assignment = Assignment.objects.create(
                    class_assigned=test_class,
                    title='Test Assignment for Email',
                    description='This is a test assignment.',
                    due_date=datetime.now().date() + timedelta(days=7),
                    teacher=teacher,
                    assignment_type='coding'
                )
            else:
                assignment = Assignment.objects.get(
                    title='Test Assignment for Email',
                    teacher=teacher
                )
            
            self.stdout.write(self.style.SUCCESS(
                '✓ Assignment creation emails test ready'
            ))
            self.stdout.write(f'  Assignment: {assignment.title}')
            self.stdout.write(f'  Teacher: {teacher.email}')
            self.stdout.write(f'  Student: {student.email}')
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ Error: {str(e)}'))

    def test_submission(self):
        """Test submission emails"""
        self.stdout.write(self.style.WARNING(
            '\n[TEST 3] Submission Emails'
        ))
        self.stdout.write('-' * 70)
        
        try:
            # Get existing data
            student = User.objects.get(username='test_student_email')
            assignment = Assignment.objects.get(title='Test Assignment for Email')
            
            # Get or create question
            question, _ = AssignmentQuestion.objects.get_or_create(
                assignment=assignment,
                title='Test Question for Email',
                defaults={'total_marks': 10.0}
            )
            
            # Create submission if it doesn't exist
            submission, created = Submission.objects.get_or_create(
                student=student,
                assignment=assignment,
                question=question,
                defaults={
                    'code': 'print("test")',
                    'status': 'submitted'
                }
            )
            
            self.stdout.write(self.style.SUCCESS(
                '✓ Submission emails test ready'
            ))
            self.stdout.write(f'  Student: {student.email}')
            self.stdout.write(f'  Assignment: {assignment.title}')
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ Error: {str(e)}'))

    def test_ai_evaluation(self):
        """Test AI evaluation emails"""
        self.stdout.write(self.style.WARNING(
            '\n[TEST 4] AI Evaluation Emails'
        ))
        self.stdout.write('-' * 70)
        
        try:
            # Get existing data
            student = User.objects.get(username='test_student_email')
            assignment = Assignment.objects.get(title='Test Assignment for Email')
            question = AssignmentQuestion.objects.get(title='Test Question for Email')
            submission = Submission.objects.get(
                student=student,
                assignment=assignment,
                question=question
            )
            
            # Create AI evaluation if it doesn't exist
            ai_eval, created = AIEvaluation.objects.get_or_create(
                submission=submission,
                defaults={
                    'assignment': assignment,
                    'question': question,
                    'student': student,
                    'question_text': question.title,
                    'student_answer': submission.code,
                    'ai_score': 8.5,
                    'confidence': 0.92,
                    'mistake_type': 'logic_error',
                    'feedback': 'Good implementation but could be optimized.',
                    'status': 'done'
                }
            )
            
            self.stdout.write(self.style.SUCCESS(
                '✓ AI evaluation emails test ready'
            ))
            self.stdout.write(f'  Student: {student.email}')
            self.stdout.write(f'  Score: {ai_eval.ai_score}')
            self.stdout.write(f'  Status: {ai_eval.status}')
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ Error: {str(e)}'))

    def print_summary(self):
        """Print email summary"""
        self.stdout.write('\n' + '=' * 70)
        self.stdout.write(self.style.SUCCESS('Test Summary'))
        self.stdout.write('=' * 70)
        
        self.stdout.write(
            f'\nTotal emails in outbox: {len(mail.outbox)}'
        )
        
        if mail.outbox:
            self.stdout.write(self.style.SUCCESS('\nEmails that would be sent:'))
            for i, email in enumerate(mail.outbox, 1):
                self.stdout.write(f'\n  {i}. {email.subject}')
                self.stdout.write(f'     From: {email.from_email}')
                self.stdout.write(f'     To: {", ".join(email.to)}')
        else:
            self.stdout.write(
                self.style.WARNING(
                    '\nℹ No emails in outbox. '
                    'Verify EMAIL_BACKEND configuration in settings.py'
                )
            )
        
        self.stdout.write('\n' + '=' * 70)
        self.stdout.write('Note: With DEBUG=True, emails may be printed to console.')
        self.stdout.write('For actual SMTP sending, configure EMAIL_BACKEND properly.')
        self.stdout.write('=' * 70 + '\n')
