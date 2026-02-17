from django.db import models
from django.contrib.auth.models import User
from django.db.models import UniqueConstraint
from django.core.validators import FileExtensionValidator
from django.core.exceptions import ValidationError
import os
import uuid

def validate_file_size(file):
    max_mb = 10  # default per-assignment can override via Assignment.max_file_size_mb if implemented in views
    if file.size > max_mb * 1024 * 1024:
        raise ValidationError(f"Max file size is {max_mb} MB")

class Profile(models.Model):
    USER_ROLES = [
        ('teacher', 'Teacher'),
        ('student', 'Student'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=10, choices=USER_ROLES)
    name = models.CharField(max_length=255, null=True, blank=True)
    enrollment_number = models.CharField(max_length=50, null=True, blank=True)
    tid = models.CharField(max_length=50, null=True, blank=True)
    
    # New fields
    contact_number = models.CharField(max_length=15, null=True, blank=True)
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    college = models.CharField(max_length=255, null=True, blank=True)
    course = models.CharField(max_length=100, null=True, blank=True)
    year = models.IntegerField(null=True, blank=True)
    batch = models.CharField(max_length=20, null=True, blank=True)
    bio = models.TextField(null=True, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    address = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"{self.user.username} ({self.role})"    

class Class(models.Model):
    class_name = models.CharField(max_length=100)
    teacher = models.ForeignKey(User, on_delete=models.CASCADE)  # Assuming the user is a teacher
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.class_name


class ClassStudent(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE)
    class_assigned = models.ForeignKey(Class, on_delete=models.CASCADE)

    class Meta:
        constraints = [
            UniqueConstraint(fields=['student', 'class_assigned'], name='unique_student_class')
        ]

    def __str__(self):
        return f"{self.student.username} - {self.class_assigned.class_name}"

class ProgrammingLanguage(models.Model):
    display_name = models.CharField(max_length=100) 
    
    piston_name = models.CharField(max_length=50, null=True, blank=True)
    piston_version = models.CharField(max_length=20, null=True, blank=True)
    
    judge0_language_id = models.IntegerField(null=True, blank=True)
    judge0_language_name = models.CharField(max_length=100, null=True, blank=True)
    
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['display_name']
        verbose_name = 'Programming Language'
        verbose_name_plural = 'Programming Languages'

    def __str__(self):
        return self.display_name
    
    language_name = models.CharField(max_length=50, null=True, blank=True)

    class Meta:
        ordering = ['display_name']
        verbose_name = 'Programming Language'
        verbose_name_plural = 'Programming Languages'

    def __str__(self):
        return self.display_name


class Assignment(models.Model):
    ASSIGNMENT_TYPE_CHOICES = [
        ('coding', 'Coding'),
        ('non_coding', 'Non-Coding'),
    ]
    
    SUBMISSION_TYPE_CHOICES = [
        ('text_only', 'Text Only'),
        ('files_only', 'Files Only'),
        ('text_and_files', 'Text and Files'),
    ]
    
    class_assigned = models.ForeignKey(Class, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    description = models.TextField()
    due_date = models.DateField()
    teacher = models.ForeignKey(User, on_delete=models.CASCADE)
    language = models.CharField(max_length=100, null=True, blank=True)
    language_version = models.CharField(max_length=50, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    assignment_type = models.CharField(
        max_length=20, 
        choices=ASSIGNMENT_TYPE_CHOICES,
        default='coding'
    )
    submission_type = models.CharField(
        max_length=20,
        choices=SUBMISSION_TYPE_CHOICES,
        default='text_only'
    )
    allowed_file_formats = models.JSONField(default=list, blank=True)
    max_file_size_mb = models.PositiveIntegerField(default=10)
    max_files_per_submission = models.PositiveIntegerField(default=5)
    
    def __str__(self):
        return self.title 
     
    def is_submitted(self):

        return Submission.objects.filter(assignment=self).exists()

class AssignmentQuestion(models.Model):
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE)
    title = models.TextField()
    total_marks = models.FloatField(default=10.0)  # Total marks for this question
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Question {self.id} for {self.assignment.title}"

class AssignmentAttachment(models.Model):

    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(
        upload_to='assignment_attachments/%Y/%m/%d/',
        validators=[FileExtensionValidator(allowed_extensions=['jpg','jpeg','png','xlsx','xls','csv','pdf','doc','docx']) , validate_file_size]
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Attachment for {self.assignment.title} ({self.file.name})"


class SubmissionFile(models.Model):
    submission = models.ForeignKey('Submission', on_delete=models.CASCADE, related_name='files')
    file = models.FileField(
        upload_to='submissions/%Y/%m/%d/',
        validators=[FileExtensionValidator(allowed_extensions=['jpg','jpeg','png','xlsx','xls','csv','pdf','doc','docx']), validate_file_size]
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"File for submission {self.submission.id} ({self.file.name})"


class Submission(models.Model):

    STATUS_CHOICES = [
        ('submitted', 'Submitted'),
        ('checked', 'Checked'),
        ('reassigned', 'Reassigned'),
        ('rejected', 'Rejected'),
    ]
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='submissions')
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name='submissions')
    question = models.ForeignKey(AssignmentQuestion, on_delete=models.CASCADE)
    code = models.TextField(blank=True, null=True)
    text_submission = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES)
    feedback = models.TextField(blank=True, null=True)
    
    # Test case related fields
    auto_marks = models.FloatField(default=0.0)  # Calculated from passed test cases
    custom_marks = models.FloatField(null=True, blank=True)  # Teacher can override
    total_testcases = models.IntegerField(default=0)  # Cache for performance
    passed_testcases = models.IntegerField(default=0)  # Cache for performance
    
    submitted_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('student', 'assignment', 'question') 
        
class TeacherFeedback(models.Model):
    submission = models.ForeignKey(Submission, on_delete=models.CASCADE)
    teacher = models.ForeignKey(User, on_delete=models.CASCADE)
    feedback = models.TextField()
    resubmission_requested = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Feedback for {self.submission} by {self.teacher.username}"


class NonCodingSubmission(models.Model):
    STATUS_CHOICES = [
        ('submitted', 'Submitted'),
        ('checked', 'Checked'),
        ('reassigned', 'Reassigned'),
        ('rejected', 'Rejected'),
    ]

    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='noncoding_submissions')
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name='noncoding_submissions')
    text_submission = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='submitted')
    feedback = models.TextField(blank=True, null=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('student', 'assignment')
        ordering = ['-submitted_at']

    def __str__(self):
        return f"NonCodingSubmission #{self.id} by {self.student.username} for {self.assignment.title}"


class NonCodingSubmissionFile(models.Model):
    submission = models.ForeignKey(NonCodingSubmission, on_delete=models.CASCADE, related_name='files')
    file = models.FileField(
        upload_to='noncoding_submissions/%Y/%m/%d/',
        validators=[FileExtensionValidator(allowed_extensions=['jpg','jpeg','png','xlsx','xls','csv','pdf','doc','docx']), validate_file_size]
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"File for NonCodingSubmission {self.submission.id} ({os.path.basename(self.file.name)})"

class TestCase(models.Model):
    question = models.ForeignKey(AssignmentQuestion, on_delete=models.CASCADE, related_name='testcases')
    input = models.TextField(blank=True, default='')
    expected_output = models.TextField(blank=True, default='')
    marks = models.IntegerField(default=1)
    visibility = models.CharField(
        max_length=10,
        choices=(("public", "Public"), ("hidden", "Hidden")),
        default="hidden"
    )
    timeout = models.IntegerField(default=2)
    memory_limit = models.IntegerField(default=128000)

    def __str__(self):
        return f"TC for {self.question_id} - {self.id}"


class TestCaseResult(models.Model):
    """Stores the result of each test case execution for a submission"""
    submission = models.ForeignKey(Submission, on_delete=models.CASCADE, related_name='testcase_results')
    testcase = models.ForeignKey(TestCase, on_delete=models.CASCADE)
    status = models.CharField(max_length=50)  # 'passed', 'failed', 'error', 'timeout'
    actual_output = models.TextField(blank=True, null=True)
    execution_time = models.FloatField(null=True, blank=True)  # in seconds
    memory_used = models.IntegerField(null=True, blank=True)  # in KB
    judge0_token = models.CharField(max_length=100, blank=True, null=True)
    error_message = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('submission', 'testcase')
    
    def __str__(self):
        return f"Result for Submission {self.submission_id} - TestCase {self.testcase_id}"

class Contact(models.Model):
    name = models.CharField(max_length=255)
    phone = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField()
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Contact from {self.name} <{self.email}>"

class AIEvaluation(models.Model):
    submission = models.OneToOneField(Submission, on_delete=models.CASCADE, related_name='ai_evaluation')
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE)
    question = models.ForeignKey(AssignmentQuestion, on_delete=models.CASCADE)
    student = models.ForeignKey(User, on_delete=models.CASCADE)

    question_text = models.TextField()
    student_answer = models.TextField()

    mistake_type = models.CharField(max_length=50, null=True, blank=True)
    ai_score = models.FloatField(null=True, blank=True)
    confidence = models.FloatField(null=True, blank=True)
    feedback = models.TextField(null=True, blank=True)

    raw_response = models.JSONField(null=True, blank=True)

    model_name = models.CharField(max_length=50, default="qwen2:1.5b-instruct-q4")
    status = models.CharField(
        max_length=20,
        choices=(("pending", "Pending"), ("done", "Done"), ("error", "Error")),
        default="pending"
    )
    error = models.TextField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"AI Eval for Submission {self.submission_id}"
