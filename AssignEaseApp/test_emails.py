"""
Test script for the Email Notification System
Run with: python manage.py shell < test_emails.py
"""

from django.core import mail
from django.contrib.auth.models import User
from AssignEaseApp.models import (
    Profile, Class, ClassStudent, Assignment, 
    AssignmentQuestion, Submission, AIEvaluation
)
from AssignEaseApp.email_service import EmailService
from datetime import datetime, timedelta

print("=" * 70)
print("AssignEase Email System Test Suite")
print("=" * 70)

# Enable console backend for testing
mail.outbox = []

# Test 1: User Registration
print("\n[TEST 1] User Registration Email")
print("-" * 70)
try:
    test_student = User.objects.create_user(
        username='emailtest_student',
        email='teststudent@example.com',
        password='testpass123',
        first_name='Test'
    )
    profile = Profile.objects.create(
        user=test_student,
        role='student',
        name='Test Student'
    )
    print("✓ User created and profile created")
    print(f"  Email: {test_student.email}")
except Exception as e:
    print(f"✗ Error: {str(e)}")

# Test 2: Assignment Creation (Teacher Email)
print("\n[TEST 2] Assignment Created - Teacher Email")
print("-" * 70)
try:
    test_teacher = User.objects.create_user(
        username='emailtest_teacher',
        email='testteacher@example.com',
        password='testpass123',
        first_name='Teacher'
    )
    teacher_profile = Profile.objects.create(
        user=test_teacher,
        role='teacher',
        name='Test Teacher'
    )
    
    test_class = Class.objects.create(
        class_name='Test Class',
        teacher=test_teacher
    )
    
    test_assignment = Assignment.objects.create(
        class_assigned=test_class,
        title='Test Assignment',
        description='This is a test assignment for email testing.',
        due_date=datetime.now().date() + timedelta(days=7),
        teacher=test_teacher,
        assignment_type='coding'
    )
    
    print("✓ Assignment created")
    print(f"  Title: {test_assignment.title}")
    print(f"  Teacher: {test_teacher.email}")
    print(f"  Class: {test_class.class_name}")
    
except Exception as e:
    print(f"✗ Error: {str(e)}")

# Test 3: Assignment Created (Student Email)
print("\n[TEST 3] Assignment Created - Student Email")
print("-" * 70)
try:
    # Enroll student in class
    class_student = ClassStudent.objects.create(
        student=test_student,
        class_assigned=test_class
    )
    print("✓ Student enrolled in class")
    print(f"  Student: {test_student.email}")
    print(f"  Class: {test_class.class_name}")
    
except Exception as e:
    print(f"✗ Error: {str(e)}")

# Test 4: Create Question and Test Case
print("\n[TEST 4] Create Assignment Question")
print("-" * 70)
try:
    test_question = AssignmentQuestion.objects.create(
        assignment=test_assignment,
        title='Write a Python function to calculate factorial',
        total_marks=10.0
    )
    print("✓ Assignment question created")
    print(f"  Question: {test_question.title}")
    
except Exception as e:
    print(f"✗ Error: {str(e)}")

# Test 5: Student Submission
print("\n[TEST 5] Student Submission Email")
print("-" * 70)
try:
    test_submission = Submission.objects.create(
        student=test_student,
        assignment=test_assignment,
        question=test_question,
        code='def factorial(n):\n    return 1 if n <= 1 else n * factorial(n-1)',
        status='submitted'
    )
    print("✓ Submission created")
    print(f"  Student: {test_student.email}")
    print(f"  Assignment: {test_assignment.title}")
    
except Exception as e:
    print(f"✗ Error: {str(e)}")

# Test 6: AI Evaluation
print("\n[TEST 6] AI Evaluation Email")
print("-" * 70)
try:
    test_ai_eval = AIEvaluation.objects.create(
        submission=test_submission,
        assignment=test_assignment,
        question=test_question,
        student=test_student,
        question_text=test_question.title,
        student_answer=test_submission.code,
        ai_score=8.5,
        confidence=0.92,
        mistake_type='logic_error',
        feedback='Good implementation but could be optimized with memoization.',
        status='done'
    )
    print("✓ AI Evaluation created and completed")
    print(f"  Student: {test_student.email}")
    print(f"  Score: {test_ai_eval.ai_score}")
    print(f"  Confidence: {test_ai_eval.confidence * 100}%")
    
except Exception as e:
    print(f"✗ Error: {str(e)}")

# Summary
print("\n" + "=" * 70)
print("Email Test Summary")
print("=" * 70)
print(f"Total emails in outbox: {len(mail.outbox)}")

if mail.outbox:
    print("\nEmails sent:")
    for i, email in enumerate(mail.outbox, 1):
        print(f"\n  {i}. Subject: {email.subject}")
        print(f"     From: {email.from_email}")
        print(f"     To: {', '.join(email.to)}")
        print(f"     Type: {'HTML' if email.alternatives else 'Plain Text'}")
else:
    print("\nℹ No emails were sent. Check if email backend is configured correctly.")

print("\n" + "=" * 70)
print("Test Complete!")
print("=" * 70)

# Cleanup (optional)
print("\n[CLEANUP] Removing test data...")
try:
    test_assignment.delete()
    test_class.delete()
    test_teacher.delete()
    test_student.delete()
    print("✓ Test data cleaned up")
except Exception as e:
    print(f"✗ Cleanup error: {str(e)}")

print("\nNote: If using console email backend, emails were printed to console.")
print("For actual SMTP sending, ensure EMAIL_BACKEND is configured in settings.py")
