from rest_framework import viewsets, generics
from rest_framework.permissions import IsAuthenticated, AllowAny
from .models import User, Profile, Class, Contact, BugReport, ClassStudent, ProgrammingLanguage, Assignment, AssignmentQuestion, CodingQuestion, CodingTestCase, NonCodingQuestion, Submission, TeacherFeedback, NonCodingSubmission, TestCase, AIEvaluation, DatabaseSchema, DatabaseQuestion, DatabaseSubmission
from .serializers import RegistrationSerializer, UserSerializer, ContactSerializer, BugReportSerializer, ProfileSerializer, ClassSerializer, ClassStudentSerializer, ProgrammingLanguageSerializer, AssignmentSerializer, AssignmentQuestionSerializer, CodingQuestionSerializer, CodingTestCaseSerializer, NonCodingQuestionSerializer, SubmissionSerializer, TeacherFeedbackSerializer, ClassStudentDetailSerializer, CustomTokenObtainPairSerializer, AssignmentAttachmentSerializer, NonCodingSubmissionSerializer, TestCaseSerializer, TestCaseResultSerializer, AIEvaluationSerializer, DatabaseSchemaSerializer, DatabaseQuestionSerializer, DatabaseSubmissionSerializer
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
from .database_service import DatabaseService

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
    
    @action(detail=False, methods=['delete'], url_path='remove-student')
    def remove_student_from_class(self, request):
        """Remove a student from a class using query parameters"""
        try:
            class_id = request.query_params.get('class_id')
            student_id = request.query_params.get('student_id')
            
            if not class_id or not student_id:
                return Response(
                    {"message": "class_id and student_id are required"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Find and delete the ClassStudent record
            class_student = ClassStudent.objects.get(
                class_assigned=class_id,
                student=student_id
            )
            class_student.delete()
            
            return Response(
                {"message": "Student successfully removed from class"},
                status=status.HTTP_200_OK
            )
        
        except ClassStudent.DoesNotExist:
            return Response(
                {"message": "Student not found in this class"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            print("Error removing student:", e)
            return Response(
                {"error": f"An error occurred: {str(e)}"},
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


class CodingQuestionViewSet(viewsets.ModelViewSet):
    """ViewSet for managing coding questions"""
    queryset = CodingQuestion.objects.all()
    serializer_class = CodingQuestionSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["assignment"]

    def get_queryset(self):
        user = self.request.user
        try:
            profile = user.profile
        except Profile.DoesNotExist:
            profile = None

        # Teachers: return coding questions for assignments they own
        if profile and profile.role == 'teacher':
            return CodingQuestion.objects.filter(assignment__teacher=user)
        # Students: return coding questions for assignments in their classes
        return CodingQuestion.objects.filter(assignment__class_assigned__in=ClassStudent.objects.filter(student=user).values_list('class_assigned', flat=True))


class CodingTestCaseViewSet(viewsets.ModelViewSet):
    """ViewSet for managing coding test cases"""
    queryset = CodingTestCase.objects.all()
    serializer_class = CodingTestCaseSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["question"]

    def get_queryset(self):
        user = self.request.user
        try:
            profile = user.profile
        except Profile.DoesNotExist:
            profile = None

        # Teachers: return test cases for questions in assignments they own
        if profile and profile.role == 'teacher':
            return CodingTestCase.objects.filter(question__assignment__teacher=user)
        # Students: no access to create/modify test cases; allow read-only for assignments in their classes
        return CodingTestCase.objects.filter(question__assignment__class_assigned__in=ClassStudent.objects.filter(student=user).values_list('class_assigned', flat=True))


class NonCodingQuestionViewSet(viewsets.ModelViewSet):
    """ViewSet for managing non-coding questions"""
    queryset = NonCodingQuestion.objects.all()
    serializer_class = NonCodingQuestionSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["assignment"]

    def get_queryset(self):
        user = self.request.user
        try:
            profile = user.profile
        except Profile.DoesNotExist:
            profile = None

        # Teachers: return non-coding questions for assignments they own
        if profile and profile.role == 'teacher':
            return NonCodingQuestion.objects.filter(assignment__teacher=user)
        # Students: return non-coding questions for assignments in their classes
        return NonCodingQuestion.objects.filter(assignment__class_assigned__in=ClassStudent.objects.filter(student=user).values_list('class_assigned', flat=True))


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


class BugReportViewSet(viewsets.ModelViewSet):
    queryset = BugReport.objects.all().order_by('-created_at')
    serializer_class = BugReportSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        try:
            profile = user.profile
        except Profile.DoesNotExist:
            profile = None

        if profile and profile.role == 'teacher':
            return BugReport.objects.all().order_by('-created_at')
        return BugReport.objects.filter(reporter=user).order_by('-created_at')

    def perform_create(self, serializer):
        serializer.save(reporter=self.request.user)


# Database Assignment Views

class DatabaseSchemaViewSet(viewsets.ModelViewSet):
    """ViewSet for managing database schemas"""
    queryset = DatabaseSchema.objects.all()
    serializer_class = DatabaseSchemaSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if user.profile.role == 'teacher':
            # Teachers can only see schemas for their assignments
            return DatabaseSchema.objects.filter(assignment__teacher=user)
        else:
            # Students can see schemas for assignments in their classes
            student_classes = ClassStudent.objects.filter(student=user).values_list('class_assigned', flat=True)
            return DatabaseSchema.objects.filter(assignment__class_assigned__in=student_classes)
 

class DatabaseQuestionViewSet(viewsets.ModelViewSet):
    """ViewSet for managing database questions"""
    queryset = DatabaseQuestion.objects.all()
    serializer_class = DatabaseQuestionSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["assignment"]
    
    def get_queryset(self):

        user = self.request.user
        assignment_id = self.request.query_params.get("assignment")

        if user.profile.role == 'teacher':
            qs = DatabaseQuestion.objects.filter(assignment__teacher=user)
        else:
            student_classes = ClassStudent.objects.filter(
                student=user
            ).values_list('class_assigned', flat=True)
    
            qs = DatabaseQuestion.objects.filter(
                assignment__class_assigned__in=student_classes
            )
    
        if assignment_id:
            qs = qs.filter(assignment_id=assignment_id)
    
        return qs


class DatabaseSubmissionViewSet(viewsets.ModelViewSet):
    """ViewSet for managing database submissions"""
    queryset = DatabaseSubmission.objects.all()
    serializer_class = DatabaseSubmissionSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if user.profile.role == 'teacher':
            # Teachers can see all submissions for their assignments
            return DatabaseSubmission.objects.filter(assignment__teacher=user)
        else:
            # Students can only see their own submissions
            return DatabaseSubmission.objects.filter(student=user)
    
    def create(self, request, *args, **kwargs):
        """Handle database submission with automatic validation"""
        student = request.user
        assignment_id = request.data.get('assignment')
        question_id = request.data.get('question')
        submitted_query = request.data.get('submitted_query')
        
        if not submitted_query or not submitted_query.strip():
            return Response(
                {'error': 'Query cannot be empty'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Get assignment, question, and schema
            assignment = Assignment.objects.get(id=assignment_id)
            question = DatabaseQuestion.objects.get(id=question_id, assignment=assignment)
            
            try:
                schema = DatabaseSchema.objects.get(assignment=assignment)
            except DatabaseSchema.DoesNotExist:
                return Response(
                    {'error': 'Database schema not found for this assignment'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Execute and validate query based on question type
            if question.question_type == 'ddl_dml':
                # For DDL/DML questions, prefer verification query when configured.
                # Older dynamic assignments may not have this field populated yet,
                # so allow submission and mark it for manual review instead of failing.
                if question.verification_query:
                    result = DatabaseService.validate_ddl_dml_query(
                        db_type=schema.db_type,
                        schema_sql=schema.schema_sql,
                        sample_data_sql=schema.sample_data_sql,
                        student_query=submitted_query,
                        verification_query=question.verification_query,
                        expected_result=question.expected_result
                    )
                else:
                    with DatabaseService.get_db_connection(schema.db_type) as conn:
                        DatabaseService.setup_schema(
                            conn,
                            schema.schema_sql,
                            schema.sample_data_sql,
                        )
                        student_result, exec_time = DatabaseService.execute_query(
                            conn,
                            submitted_query,
                            schema.db_type,
                            allow_write_operations=True
                        )

                    result = {
                        'is_correct': False,
                        'query_result': student_result,
                        'execution_time': exec_time,
                        'error_message': None,
                        'feedback': 'Query executed successfully, but auto-verification is unavailable for this question. Manual review required.',
                    }
            else:
                # For SELECT questions, direct validation
                result = DatabaseService.execute_and_validate(
                    db_type=schema.db_type,
                    schema_sql=schema.schema_sql,
                    sample_data_sql=schema.sample_data_sql,
                    student_query=submitted_query,
                    expected_result=question.expected_result,
                    allow_write_operations=False
                )
            
            # Calculate marks
            auto_marks = question.total_marks if result['is_correct'] else 0.0
            
            # Create or update submission
            submission, created = DatabaseSubmission.objects.update_or_create(
                student=student,
                assignment=assignment,
                question=question,
                defaults={
                    'submitted_query': submitted_query,
                    'query_result': result['query_result'],
                    'is_correct': result['is_correct'],
                    'execution_time': result['execution_time'],
                    'error_message': result['error_message'],
                    'auto_marks': auto_marks,
                    'feedback': result['feedback'],
                    'status': 'submitted'
                }
            )
            
            serializer = self.get_serializer(submission)
            return Response(
                serializer.data,
                status=status.HTTP_201_CREATED if created else status.HTTP_200_OK
            )
            
        except Assignment.DoesNotExist:
            return Response(
                {'error': 'Assignment not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except DatabaseQuestion.DoesNotExist:
            return Response(
                {'error': 'Question not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': f'Submission failed: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )


class TestDatabaseQueryView(APIView):
    """Test query without submitting (for students to practice)"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        assignment_id = request.data.get('assignment_id')
        query = request.data.get('query')
        
        if not query or not query.strip():
            return Response(
                {'success': False, 'error': 'Query cannot be empty'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            assignment = Assignment.objects.get(id=assignment_id)
            
            try:
                schema = DatabaseSchema.objects.get(assignment=assignment)
            except DatabaseSchema.DoesNotExist:
                return Response(
                    {'success': False, 'error': 'Database schema not found for this assignment'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Execute query without validation (just show results)
            with DatabaseService.get_db_connection(schema.db_type) as conn:
                DatabaseService.setup_schema(conn, schema.schema_sql, schema.sample_data_sql)
                result, exec_time = DatabaseService.execute_query(conn, query, schema.db_type)
            
            return Response({
                'success': True,
                'result': result,
                'execution_time': exec_time,
                'row_count': len(result)
            })
            
        except Assignment.DoesNotExist:
            return Response(
                {'success': False, 'error': 'Assignment not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'success': False, 'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class TestDatabaseSchemaView(APIView):
    """Test database schema without requiring a saved assignment"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        db_type = request.data.get('db_type', 'sqlite')
        schema_sql = request.data.get('schema_sql', '')
        sample_data_sql = request.data.get('sample_data_sql', '')
        
        if not schema_sql or not schema_sql.strip():
            return Response(
                {'success': False, 'error': 'Schema SQL cannot be empty'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Test the schema by creating tables and inserting sample data
            with DatabaseService.get_db_connection(db_type) as conn:
                DatabaseService.setup_schema(conn, schema_sql, sample_data_sql)
                
                # If we get here, schema is valid
                # Count how many tables were created
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = cursor.fetchall()
                table_names = [table[0] for table in tables]
                cursor.close()
            
            return Response({
                'success': True,
                'message': f'Schema is valid! Created {len(table_names)} table(s).',
                'tables': table_names
            })
            
        except Exception as e:
            return Response(
                {'success': False, 'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class TestDatabaseQueryWithSchemaView(APIView):
    """Test query with provided schema (for question creation before assignment is saved)"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        db_type = request.data.get('db_type', 'sqlite')
        schema_sql = request.data.get('schema_sql', '')
        sample_data_sql = request.data.get('sample_data_sql', '')
        query = request.data.get('query', '')
        allow_write = request.data.get('allow_write_operations', False)
        
        if not schema_sql or not schema_sql.strip():
            return Response(
                {'success': False, 'error': 'Schema SQL cannot be empty'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not query or not query.strip():
            return Response(
                {'success': False, 'error': 'Query cannot be empty'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Execute query against the provided schema
            with DatabaseService.get_db_connection(db_type) as conn:
                DatabaseService.setup_schema(conn, schema_sql, sample_data_sql)
                result, exec_time = DatabaseService.execute_query(conn, query, db_type, allow_write)
            
            return Response({
                'success': True,
                'result': result,
                'execution_time': exec_time,
                'row_count': len(result) if result else 0
            })
            
        except Exception as e:
            return Response(
                {'success': False, 'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


@api_view(['GET'])
def get_database_submissions_by_student(request, student_id, assignment_id):
    """Get all database submissions for a student in a specific assignment"""
    try:
        submissions = DatabaseSubmission.objects.filter(
            student_id=student_id,
            assignment_id=assignment_id
        ).order_by('question__order')
        
        serializer = DatabaseSubmissionSerializer(submissions, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )


class GenerateDatabaseAssignmentWithAIView(APIView):
    """Generate database assignment schema and questions using AI"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        user = request.user
        
        # Check teacher role
        try:
            profile = user.profile
            if profile.role != 'teacher':
                return Response(
                    {"error": "Only teachers can generate assignments with AI"},
                    status=status.HTTP_403_FORBIDDEN
                )
        except Profile.DoesNotExist:
            return Response(
                {"error": "User profile not found"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        questions = request.data.get('questions', [])
        
        if not questions or not isinstance(questions, list):
            return Response(
                {"error": "questions must be a non-empty list"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if len(questions) > 20:
            return Response(
                {"error": "Maximum 20 questions allowed"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"AI generation requested for {len(questions)} questions")
            
            from .llm import generate_database_assignment
            
            logger.info("Starting AI database assignment generation...")
            result = generate_database_assignment(questions)
            logger.info("AI generation completed successfully")
            
            # Validate the result
            if not result.get('schema_sql'):
                raise ValueError("No schema generated")
            if not result.get('questions'):
                raise ValueError("No questions generated")
            
            logger.info(f"Generated {len(result.get('questions', []))} questions with schema")
            return Response(result, status=status.HTTP_200_OK)
        
        except Exception as e:
            import logging
            import traceback
            logger = logging.getLogger(__name__)
            logger.error(f"AI generation error: {str(e)}")
            logger.error(traceback.format_exc())
            
            return Response(
                {"error": f"AI generation failed: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
