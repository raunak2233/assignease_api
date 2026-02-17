from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import RegisterView, UserViewSet, ProfileViewSet,UpdateSubmissionStatus,AssignmentByQuestionView, StudentDetailView, AssignmentListView, ClassViewSet, StudentSubmissionsView, TestCaseViewSet, ClassStudentViewSet,ClassSimpleDetailView, AssignmentDetailView, ProgrammingLanguageViewSet, AssignmentViewSet, AssignmentQuestionViewSet, SubmissionViewSet, TeacherFeedbackViewSet, JoinedClassesView, AssignmentAttachmentViewSet, NonCodingSubmissionViewSet, RunTestCasesView, EvaluateSubmissionView, CustomTokenObtainPairView, DeleteClassView, get_students_in_class, student_performance, TestCaseResultViewSet, ContactViewSet
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .oauth_views import GoogleOAuthView, GitHubOAuthView
from .otp_views import SendOTPView, VerifyOTPView, ResetPasswordView
from . import views
router = DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'profiles', ProfileViewSet)
router.register(r'classes', ClassViewSet)
router.register(r'classstudents', ClassStudentViewSet)
router.register(r'programminglanguages', ProgrammingLanguageViewSet)
router.register(r'assignments', AssignmentViewSet)
router.register(r'assignmentquestions', AssignmentQuestionViewSet)
router.register(r'testcases', TestCaseViewSet)
router.register(r'testcaseresults', TestCaseResultViewSet)
router.register(r'contact', ContactViewSet)
router.register(r'assignmentattachments', AssignmentAttachmentViewSet)
router.register(r'submissions', SubmissionViewSet)
router.register(r'noncodingsubmissions', NonCodingSubmissionViewSet)
router.register(r'teacherfeedback', TeacherFeedbackViewSet)
  
urlpatterns = [
    path('', include(router.urls)),
    path('register/', RegisterView.as_view(), name='register'),
    path('api/token/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/google/', GoogleOAuthView.as_view(), name='google-oauth'),
    path('auth/github/', GitHubOAuthView.as_view(), name='github-oauth'),
    path('otp/send/', SendOTPView.as_view(), name='send-otp'),
    path('otp/verify/', VerifyOTPView.as_view(), name='verify-otp'),
    path('otp/reset-password/', ResetPasswordView.as_view(), name='reset-password'),
    path('joined-classes/', JoinedClassesView.as_view(), name='joined-classes'),
    path('class/simple/<int:class_id>/', ClassSimpleDetailView.as_view(), name='class-simple-detail'),
    path('class/<int:class_id>/students/', get_students_in_class, name='get_students_in_class'),
    path('student_assignments/<int:student_id>/', views.get_student_assignments, name='student-assignments'),
    path('classstudents/<int:class_assigned>/students/', views.get_students_in_class, name='student-class'),
    path('assignment_details/<int:pk>/', AssignmentDetailView.as_view(), name='assignment-detail'),
    path('assignment-details/<int:class_assigned_id>/', AssignmentListView.as_view(), name='assignment-list'),
    path("submissions/student/<int:student_id>/", StudentSubmissionsView.as_view(), name="student-submissions"),
    path('student/<int:student_id>/', StudentDetailView.as_view(), name='student-detail'),
    path('assignment-by-question/<int:question_id>/', AssignmentByQuestionView.as_view(), name='assignment-by-question'),
    path('submissions/<int:submission_id>/update-status/', UpdateSubmissionStatus.as_view(), name='update-submission-status'),
    path('classes/<int:pk>/delete/', DeleteClassView.as_view(), name='delete-class'),
    path('student-performance/<int:student_id>/', student_performance, name='student-performance'),
    
    # TestCase endpoints
    path("run-testcases/", RunTestCasesView.as_view(), name="run-testcases"),
    path("evaluate-submission/", EvaluateSubmissionView.as_view(), name="evaluate-submission"),
    path('ai-evaluations/', views.AIEvaluationListView.as_view(), name='ai-evaluation-list'),
    path('ai-evaluations/<int:pk>/', views.AIEvaluationDetailView.as_view(), name='ai-evaluation-detail')
]