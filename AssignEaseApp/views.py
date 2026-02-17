from rest_framework import viewsets, generics
from rest_framework.permissions import IsAuthenticated, AllowAny
from .models import User, Profile, Class, Contact, ClassStudent, ProgrammingLanguage, Assignment, AssignmentQuestion, Submission, TeacherFeedback, NonCodingSubmission, TestCase, AIEvaluation
from .serializers import RegistrationSerializer, UserSerializer, ContactSerializer, ProfileSerializer, ClassSerializer, ClassStudentSerializer, ProgrammingLanguageSerializer, AssignmentSerializer, AssignmentQuestionSerializer, SubmissionSerializer, TeacherFeedbackSerializer, ClassStudentDetailSerializer, CustomTokenObtainPairSerializer, AssignmentAttachmentSerializer, NonCodingSubmissionSerializer, TestCaseSerializer, TestCaseResultSerializer, AIEvaluationSerializer
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import Assignment, ClassStudent
from rest_framework.views import APIView
from django.db.models import Exists, OuterRef, Q
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser
from .models import AssignmentAttachment
from .piston_service import PistonService
from .models import AssignmentQuestion, TestCase, TestCaseResult

@api_view(['GET'])
def get_student_assignments(request, student_id):
    try:
        student_classes = ClassStudent.objects.filter(student_id=student_id)
        class_ids = student_classes.values_list('class_assigned', flat=True)

        assignments = Assignment.objects.filter(class_assigned__in=class_ids)

        serialized_assignments = AssignmentSerializer(
            assignments, 
            many=True, 
            context={'student_id': student_id} 
        )

        return Response(serialized_assignments.data, status=200)

    except Exception as e:
        return Response({"error": str(e)}, status=400)


    
@api_view(['GET'])
def get_students_in_class(request, class_id):
    class_instance = get_object_or_404(Class, id=class_id)

    class_students = ClassStudent.objects.filter(class_assigned=class_instance)

    serializer = ClassStudentSerializer(class_students, many=True)

    return Response(serializer.data)

class AssignmentDetailView(generics.RetrieveAPIView):
    queryset = Assignment.objects.all()
    serializer_class = AssignmentSerializer



class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Get the tokens
        tokens = serializer.validated_data

        # Fetch the user's role
        user = serializer.user
        role = user.profile.role if hasattr(user, 'profile') else None  # Safely access the profile

        # Construct the response
        return Response({
            'refresh': tokens['refresh'],
            'access': tokens['access'],
            'role': role,  # Include the role in the response
        })

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]  # Require authentication for this view


class RegisterView(generics.CreateAPIView):
    serializer_class = RegistrationSerializer
    permission_classes = []
    def create(self, request, *args, **kwargs):
        from .email_service import EmailService
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        # Send registration confirmation email
        try:
            role = request.data.get('role', 'student')
            EmailService.send_student_registration_confirmation(user, role)
        except Exception as e:
            # Log error but don't fail the registration
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to send registration email: {str(e)}")
        
        return Response({
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
            }
        }, status=status.HTTP_201_CREATED)


class StudentDetailView(APIView):
    def get(self, request, student_id):
        try:
            student_profile = Profile.objects.get(user_id=student_id)
            serializer = ProfileSerializer(student_profile)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Profile.DoesNotExist:
            return Response({"error": "Student not found"}, status=status.HTTP_404_NOT_FOUND)


class StudentSubmissionsView(APIView):
    def get(self, request, student_id):
        submissions = Submission.objects.filter(student=student_id)
        if not submissions.exists():
            return Response({"message": "No submissions found for this student."}, status=status.HTTP_404_NOT_FOUND)
        serializer = SubmissionSerializer(submissions, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class AssignmentByQuestionView(APIView):
    def get(self, request, question_id):
        try:
            submission = Submission.objects.get(question_id=question_id)
            assignment = submission.assignment
            serializer = AssignmentSerializer(assignment)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Submission.DoesNotExist:
            return Response({"error": "Submission with this question ID not found"}, status=status.HTTP_404_NOT_FOUND)


class UpdateSubmissionStatus(APIView):
    def patch(self, request, submission_id):
        try:
            submission = Submission.objects.get(id=submission_id)
        except Submission.DoesNotExist:
            return Response({"detail": "Submission not found"}, status=status.HTTP_404_NOT_FOUND)
        
        new_status = request.data.get('status')
        if new_status not in dict(Submission.STATUS_CHOICES):
            return Response({"detail": "Invalid status"}, status=status.HTTP_400_BAD_REQUEST)
        
        submission.status = new_status
        submission.save()
        
        return Response({"detail": "Submission status updated successfully"}, status=status.HTTP_200_OK)


class ProfileViewSet(viewsets.ModelViewSet):
    queryset = Profile.objects.all()
    serializer_class = ProfileSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    
    def get_queryset(self):
        """
        Return only the profile belonging to the authenticated user.
        This ensures GET /profiles/ (list) returns only the profile whose token is provided.
        """
        user = self.request.user
        if not user or not user.is_authenticated:
            return Profile.objects.none()
        return Profile.objects.filter(user=user)
    
    def get_object(self):
        """
        Override get_object to handle role-based access
        Teachers: Can access any profile
        Students: Can only access their own profile
        """
        profile_id = self.kwargs.get('pk')
        user = self.request.user
        
        try:
            user_profile = user.profile
        except Profile.DoesNotExist:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied('User profile not found')
        
        # Teachers can access any profile
        if user_profile.role == 'teacher':
            try:
                return Profile.objects.get(pk=profile_id)
            except Profile.DoesNotExist:
                from rest_framework.exceptions import NotFound
                raise NotFound('Profile not found')
        
        # Students can only access their own profile
        try:
            profile = Profile.objects.get(pk=profile_id)
            if profile.user != user:
                from rest_framework.exceptions import PermissionDenied
                raise PermissionDenied('You do not have permission to view this profile')
            return profile
        except Profile.DoesNotExist:
            from rest_framework.exceptions import NotFound
            raise NotFound('Profile not found')

    def retrieve(self, request, *args, **kwargs):
        """
        Retrieve a specific profile
        Permission checking is done in get_object()
        """
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def list(self, request, *args, **kwargs):
        """
        List profiles
        Teachers: Get all profiles
        Students: Get only their own profile
        """
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def update(self, request, *args, **kwargs):
        """
        Update profile
        Users can only update their own profile
        """
        partial = kwargs.pop('partial', False)
        instance = self.get_object()  # This will check if user can access the profile
        
        # Additional check: users can only update their own profile
        if instance.user != request.user:
            return Response(
                {'error': 'You can only update your own profile'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        
        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        """
        Delete profile - only own profile can be deleted
        """
        instance = self.get_object()  # This will check if user can access the profile
        
        # Additional check: users can only delete their own profile
        if instance.user != request.user:
            return Response(
                {'error': 'You can only delete your own profile'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)

class ClassViewSet(viewsets.ModelViewSet):
    queryset = Class.objects.all()
    serializer_class = ClassSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Class.objects.filter(teacher_id=self.request.user)

class ClassSimpleDetailView(APIView):
    def get(self, request, class_id):
        try:
            class_instance = Class.objects.only('id', 'class_name').get(id=class_id)
            return Response(
                {"id": class_instance.id, "class_name": class_instance.class_name},
                status=status.HTTP_200_OK
            )
        except Class.DoesNotExist:
            return Response(
                {"error": "Class not found."},
                status=status.HTTP_404_NOT_FOUND
            )



class JoinedClassesView(generics.ListAPIView):
    serializer_class = ClassStudentDetailSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            raise Exception("User is not authenticated")

        queryset = ClassStudent.objects.filter(student=user)
        print(f"Queryset: {queryset}")

        if not queryset.exists():
            print("No classes found for this student.") 
        else:
            print(f"Classes found: {queryset.count()}")

        return queryset

class AssignmentListView(APIView):
    def get(self, request, class_assigned_id):
        assignments = Assignment.objects.filter(class_assigned__id=class_assigned_id)
        
        if not assignments.exists():
            return Response({"detail": "No assignments found for this class ID."}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = AssignmentSerializer(assignments, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)




class ClassStudentViewSet(viewsets.ModelViewSet):
    queryset = ClassStudent.objects.all()
    serializer_class = ClassStudentSerializer
    permission_classes = [IsAuthenticated]
    
    @action(detail=True, methods=['get'], url_path='students')
    
    def get_students_in_class(self, request, pk=None):
        try:
            # Filter students by class_assigned
            students = ClassStudent.objects.filter(class_assigned=pk)
            if not students.exists():
                return Response(
                    {"message": "No students found in this class."},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Serialize the data
            serializer = self.get_serializer(students, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        
        except Exception as e:
            print("Error:", e)
            return Response(
                {"error": "An unexpected error occurred."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        print(queryset)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class ProgrammingLanguageViewSet(viewsets.ModelViewSet):
    queryset = ProgrammingLanguage.objects.all()
    serializer_class = ProgrammingLanguageSerializer
    permission_classes = [IsAuthenticated]

class AssignmentViewSet(viewsets.ModelViewSet):
    queryset = Assignment.objects.all()
    serializer_class = AssignmentSerializer
    permission_classes = [IsAuthenticated]

class AssignmentQuestionViewSet(viewsets.ModelViewSet):
    queryset = AssignmentQuestion.objects.all()
    serializer_class = AssignmentQuestionSerializer
    permission_classes = [IsAuthenticated]

class SubmissionViewSet(viewsets.ModelViewSet):
    queryset = Submission.objects.all()
    serializer_class = SubmissionSerializer
    permission_classes = [IsAuthenticated] 


    def get_queryset(self):
        user = self.request.user
        profile = user.profile 

        queryset = Submission.objects.all()

        if profile.role == 'teacher':
            # Fetch only submissions for assignments created by this teacher
            queryset = queryset.filter(assignment__teacher=user)
        else:
            # If the user is a student (check the profile's role)
            queryset = queryset.filter(student=user)

        # Apply query parameter filters
        assignment_id = self.request.query_params.get('assignment')
        if assignment_id:
            queryset = queryset.filter(assignment_id=assignment_id)

        student_id = self.request.query_params.get('student')
        if student_id:
            queryset = queryset.filter(student_id=student_id)

        question_id = self.request.query_params.get('question')
        if question_id:
            queryset = queryset.filter(question_id=question_id)

        return queryset




class TeacherFeedbackViewSet(viewsets.ModelViewSet):
    queryset = TeacherFeedback.objects.all()
    serializer_class = TeacherFeedbackSerializer
    permission_classes = [IsAuthenticated]



class DeleteClassView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk, format=None):
        try:
            # Get the class by id
            class_instance = get_object_or_404(Class, pk=pk)

            if class_instance.teacher != request.user:
                return Response(
                    {"error": "You are not authorized to delete this class."},
                    status=status.HTTP_403_FORBIDDEN
                )

            class_instance.delete()
            return Response({"message": "Class deleted successfully."}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {"error": f"An error occurred: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
@api_view(['GET'])
def student_performance(request, student_id):
    try:
        # Total assignments assigned
        assigned_classes = ClassStudent.objects.filter(student_id=student_id).values_list("class_assigned", flat=True)
        total_assignments = Assignment.objects.filter(class_assigned__in=assigned_classes).count()

        # Submissions breakdown
        submissions = Submission.objects.filter(student_id=student_id)
        submitted_count = submissions.count()
        checked_count = submissions.filter(status="checked").count()
        reassigned_count = submissions.filter(status="reassigned").count()
        rejected_count = submissions.filter(status="rejected").count()

        performance_data = {
            "total_assignments": total_assignments,
            "submitted": submitted_count,
            "checked": checked_count,
            "reassigned": reassigned_count,
            "rejected": rejected_count,
        }

        return Response(performance_data)

    except Exception as e:
        return Response({"error": str(e)}, status=400)

class AssignmentAttachmentViewSet(viewsets.ModelViewSet):
    queryset = AssignmentAttachment.objects.all()
    serializer_class = AssignmentAttachmentSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def perform_create(self, serializer):
        serializer.save()

# New viewset for non-coding submissions
class NonCodingSubmissionViewSet(viewsets.ModelViewSet):
    queryset = NonCodingSubmission.objects.all()
    serializer_class = NonCodingSubmissionSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def get_queryset(self):
        user = self.request.user
        try:
            profile = user.profile
        except Profile.DoesNotExist:
            profile = None

        queryset = NonCodingSubmission.objects.all()

        # Filter by role
        if profile and profile.role == 'teacher':
            # teachers see all non-coding submissions for their assignments
            queryset = queryset.filter(assignment__teacher=user)
        else:
            # students see their own
            queryset = queryset.filter(student=user)

        # Apply query parameter filters
        assignment_id = self.request.query_params.get('assignment')
        if assignment_id:
            queryset = queryset.filter(assignment_id=assignment_id)

        student_id = self.request.query_params.get('student')
        if student_id:
            queryset = queryset.filter(student_id=student_id)

        return queryset

    def perform_create(self, serializer):
        serializer.save()

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        
        # Allow teachers to update status and feedback
        # Allow students to update their own submissions (before final submission)
        user = request.user
        try:
            profile = user.profile
        except Profile.DoesNotExist:
            return Response(
                {"error": "User profile not found"}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check permissions
        if profile.role == 'teacher':
            # Teachers can update submissions for their assignments
            if instance.assignment.teacher != user:
                return Response(
                    {"error": "You can only update submissions for your assignments"}, 
                    status=status.HTTP_403_FORBIDDEN
                )
        elif profile.role == 'student':
            # Students can only update their own submissions
            if instance.student != user:
                return Response(
                    {"error": "You can only update your own submissions"}, 
                    status=status.HTTP_403_FORBIDDEN
                )

        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        return Response(serializer.data)

    def perform_update(self, serializer):
        serializer.save()

    def patch(self, request, *args, **kwargs):
        """
        Custom PATCH method for list endpoint to update submission by assignment ID
        URL: PATCH /noncodingsubmissions/
        Data: {"assignment": assignment_id, "status": "new_status", "feedback": "optional feedback"}
        """
        user = request.user
        try:
            profile = user.profile
        except Profile.DoesNotExist:
            return Response(
                {"error": "User profile not found"}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        assignment_id = request.data.get('assignment')
        if not assignment_id:
            return Response(
                {"error": "Assignment ID is required"}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            assignment = Assignment.objects.get(id=assignment_id)
        except Assignment.DoesNotExist:
            return Response(
                {"error": "Assignment not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )

        # Find the submission for this assignment
        if profile.role == 'teacher':
            # Teachers can update submissions for their assignments
            if assignment.teacher != user:
                return Response(
                    {"error": "You can only update submissions for your assignments"}, 
                    status=status.HTTP_403_FORBIDDEN
                )
            # Find any student's submission for this assignment (teacher can update any)
            try:
                submission = NonCodingSubmission.objects.get(assignment=assignment)
            except NonCodingSubmission.DoesNotExist:
                return Response(
                    {"error": "No submission found for this assignment"}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            except NonCodingSubmission.MultipleObjectsReturned:
                # If multiple submissions exist, we need student ID too
                student_id = request.data.get('student')
                if not student_id:
                    return Response(
                        {"error": "Multiple submissions found. Please specify student ID"}, 
                        status=status.HTTP_400_BAD_REQUEST
                    )
                try:
                    submission = NonCodingSubmission.objects.get(assignment=assignment, student_id=student_id)
                except NonCodingSubmission.DoesNotExist:
                    return Response(
                        {"error": "No submission found for this assignment and student"}, 
                        status=status.HTTP_404_NOT_FOUND
                    )

        elif profile.role == 'student':
            # Students can only update their own submissions
            try:
                submission = NonCodingSubmission.objects.get(assignment=assignment, student=user)
            except NonCodingSubmission.DoesNotExist:
                return Response(
                    {"error": "No submission found for this assignment"}, 
                    status=status.HTTP_404_NOT_FOUND
                )
        else:
            return Response(
                {"error": "Invalid user role"}, 
                status=status.HTTP_403_FORBIDDEN
            )

        # Update the submission
        serializer = self.get_serializer(submission, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data, status=status.HTTP_200_OK)

# New viewset for TestCase
class TestCaseViewSet(viewsets.ModelViewSet):
    queryset = TestCase.objects.all()
    serializer_class = TestCaseSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        try:
            profile = user.profile
        except Profile.DoesNotExist:
            profile = None

        # Teachers: return testcases for questions in assignments they own
        if profile and profile.role == 'teacher':
            return TestCase.objects.filter(question__assignment__teacher=user)
        # Students: no access to create/modify testcases; allow read-only on testcases for questions in their classes' assignments
        # Return testcases only for assignments assigned to student's classes
        return TestCase.objects.filter(question__assignment__class_assigned__in=ClassStudent.objects.filter(student=user).values_list('class_assigned', flat=True))



class RunTestCasesView(APIView): 
    permission_classes = [IsAuthenticated]

    def post(self, request):
        question_id = request.data.get('question_id')
        source_code = request.data.get('source_code')
        language_name = request.data.get('language_name')
        version = request.data.get('language_version')

        if not all([question_id, source_code, language_name, version]):
            return Response(
                {"error": "question_id, source_code, language_name, language_version are required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            question = AssignmentQuestion.objects.get(id=question_id)
        except AssignmentQuestion.DoesNotExist:
            return Response({"error": "Question not found"}, status=status.HTTP_404_NOT_FOUND)

        testcases = TestCase.objects.filter(question=question, visibility='public')

        if not testcases.exists():
            return Response({
                "message": "No public test cases for this question",
                "results": [],
                "total": 0,
                "passed": 0
            })

        results = []

        for tc in testcases:
            response = PistonService.run_code(
                source_code=source_code,
                language=language_name,
                version=version,
                stdin=tc.input
            )

            stdout = response.get("stdout", "").strip()
            stderr = response.get("stderr", "")

            passed = (stdout == tc.expected_output.strip()) and stderr == ""

            results.append({
                "testcase_id": tc.id,
                "input": tc.input,
                "expected_output": tc.expected_output,
                "actual_output": stdout,
                "error_message": stderr,
                "passed": passed
            })

        return Response({
            "results": results,
            "total": len(results),
            "passed": sum(r["passed"] for r in results)
        })

class EvaluateSubmissionView(APIView):
    """
    Evaluate all test cases for a submission after student submits
    POST /api/evaluate-submission/
    Body: {"submission_id": 1}
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        submission_id = request.data.get("submission_id")

        if not submission_id:
            return Response({"error": "submission_id is required"},
                            status=status.HTTP_400_BAD_REQUEST)

        try:
            submission = Submission.objects.get(id=submission_id)
        except Submission.DoesNotExist:
            return Response({"error": "Submission not found"},
                            status=status.HTTP_404_NOT_FOUND)

        question = submission.question
        testcases = TestCase.objects.filter(question=question)

        if not testcases.exists():
            return Response({
                "message": "No test cases for this question",
                "auto_marks": 0,
                "passed_testcases": 0,
                "total_testcases": 0
            })

        # Resolve language and version for Piston:
        assignment = submission.assignment
        piston_language = None
        piston_version = assignment.language_version or ""

        if assignment.language:
            # Try to find a ProgrammingLanguage matching common fields
            pl = ProgrammingLanguage.objects.filter(
                Q(piston_name__iexact=assignment.language) |
                Q(display_name__iexact=assignment.language) |
                Q(language_name__iexact=assignment.language)
            ).first()
            if pl:
                piston_language = pl.piston_name or pl.language_name or pl.display_name
                # prefer explicit version from assignment, otherwise PL's version
                if not piston_version:
                    piston_version = pl.piston_version or ""
            else:
                # fallback to raw assignment.language (user might have stored piston name there)
                piston_language = assignment.language

        if not piston_language:
            return Response({"error": "No language configured for assignment"},
                            status=status.HTTP_400_BAD_REQUEST)

        passed_count = 0
        total_count = testcases.count()

        for tc in testcases:
            # Use the same param names as other runs (source_code)
            result = PistonService.run_code(
                source_code=submission.code,
                language=piston_language,
                version=piston_version,
                stdin=tc.input
            )

            stdout = (result.get("stdout") or "").strip()
            stderr = result.get("stderr") or ""

            passed = (stdout == (tc.expected_output or "").strip()) and stderr == ""

            # Save result
            TestCaseResult.objects.update_or_create(
                submission=submission,
                testcase=tc,
                defaults={
                    "status": "passed" if passed else "failed",
                    "actual_output": stdout,
                    "error_message": stderr,
                }
            )

            if passed:
                passed_count += 1

        total_marks = question.total_marks
        auto_marks = (passed_count / total_count) * total_marks if total_count else 0

        submission.total_testcases = total_count
        submission.passed_testcases = passed_count
        submission.auto_marks = auto_marks
        submission.save()

        return Response({
            "submission_id": submission.id,
            "total_testcases": total_count,
            "passed_testcases": passed_count,
            "auto_marks": auto_marks,
            "percentage": (passed_count / total_count * 100) if total_count else 0
        })

# New viewset to CRUD TestCaseResult
class TestCaseResultViewSet(viewsets.ModelViewSet):
    queryset = TestCaseResult.objects.all()
    serializer_class = TestCaseResultSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        try:
            profile = user.profile
        except Profile.DoesNotExist:
            profile = None

        # Teachers: see results for submissions of assignments they own
        if profile and profile.role == 'teacher':
            return TestCaseResult.objects.filter(submission__assignment__teacher=user)
        # Students: see only their own submission results
        return TestCaseResult.objects.filter(submission__student=user)


class AIEvaluationListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        try:
            profile = user.profile
        except Profile.DoesNotExist:
            return Response({"error": "User profile not found"}, status=status.HTTP_400_BAD_REQUEST)

        if profile.role == 'teacher':
            qs = AIEvaluation.objects.filter(assignment__teacher=user)
        else:
            qs = AIEvaluation.objects.filter(student=user)

        serializer = AIEvaluationSerializer(qs, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class AIEvaluationDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            ai = AIEvaluation.objects.get(pk=pk)
        except AIEvaluation.DoesNotExist:
            return Response({"error": "AI evaluation not found"}, status=status.HTTP_404_NOT_FOUND)

        user = request.user
        try:
            profile = user.profile
        except Profile.DoesNotExist:
            return Response({"error": "User profile not found"}, status=status.HTTP_400_BAD_REQUEST)

        if profile.role == 'teacher':
            if ai.assignment.teacher != user:
                return Response({"error": "You do not have permission to view this resource"}, status=status.HTTP_403_FORBIDDEN)
        else:
            if ai.student != user:
                return Response({"error": "You do not have permission to view this resource"}, status=status.HTTP_403_FORBIDDEN)

        serializer = AIEvaluationSerializer(ai, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

class ContactViewSet(viewsets.ModelViewSet):
    queryset = Contact.objects.all().order_by('-created_at')
    serializer_class = ContactSerializer
    permission_classes = [AllowAny]