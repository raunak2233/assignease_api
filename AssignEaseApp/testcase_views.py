# from rest_framework.views import APIView
# from rest_framework.response import Response
# from rest_framework import status
# from rest_framework.permissions import IsAuthenticated
# from .models import AssignmentQuestion, TestCase, Submission, TestCaseResult, Assignment
# from .serializers import TestCaseResultSerializer
# from .judge0_service import Judge0Service


# class RunTestCasesView(APIView):
#     """
#     Student endpoint to run test cases before submission
#     POST /api/run-testcases/
#     Body: {
#         "question_id": 1,
#         "source_code": "print('hello')",
#         "language_id": 71
#     }
#     """ 
#     permission_classes = [IsAuthenticated]
    
#     def post(self, request):
#         question_id = request.data.get('question_id')
#         source_code = request.data.get('source_code')
#         language_id = request.data.get('language_id')

        
#         if not all([question_id, source_code, language_id]):
#             return Response(
#                 {"error": "question_id, source_code, and language_id are required"},
#                 status=status.HTTP_400_BAD_REQUEST
#             )
        
#         try:
#             question = AssignmentQuestion.objects.get(id=question_id)
#         except AssignmentQuestion.DoesNotExist:
#             return Response(
#                 {"error": "Question not found"},
#                 status=status.HTTP_404_NOT_FOUND
#             )
        
#         testcases = TestCase.objects.filter(question=question, visibility='public')
        
#         if not testcases.exists():
#             return Response({
#                 "message": "No public test cases available for this question",
#                 "results": [],
#                 "total": 0,
#                 "passed": 0
#             })
        
#         results = []
#         for tc in testcases:
#             result = Judge0Service.evaluate_testcase(source_code, language_id, tc)
#             results.append({
#                 "testcase_id": tc.id,
#                 "input": tc.input,
#                 "expected_output": tc.expected_output,
#                 "status": result["status"],
#                 "passed": result["passed"],
#                 "actual_output": result.get("actual_output", ""),
#                 "error_message": result.get("error_message", ""),
#                 "execution_time": result.get("execution_time"),
#                 "memory_used": result.get("memory_used"),
#             })
        
#         return Response({
#             "results": results,
#             "total": len(results),
#             "passed": sum(1 for r in results if r["passed"])
#         })


# class EvaluateSubmissionView(APIView):
#     """
#     Evaluate all test cases for a submission (called after student submits)
#     POST /api/evaluate-submission/
#     Body: {"submission_id": 1}
#     """
#     permission_classes = [IsAuthenticated]
    
#     def post(self, request):
#         submission_id = request.data.get('submission_id')
        
#         if not submission_id:
#             return Response(
#                 {"error": "submission_id is required"},
#                 status=status.HTTP_400_BAD_REQUEST
#             )
        
#         try:
#             submission = Submission.objects.get(id=submission_id)
#         except Submission.DoesNotExist:
#             return Response(
#                 {"error": "Submission not found"},
#                 status=status.HTTP_404_NOT_FOUND
#             )
        
#         # Check if submission has code
#         if not submission.code:
#             return Response(
#                 {"error": "Submission has no code to evaluate"},
#                 status=status.HTTP_400_BAD_REQUEST
#             )
        
#         # Get all test cases for this question
#         testcases = TestCase.objects.filter(question=submission.question)
        
#         if not testcases.exists():
#             return Response(
#                 {"message": "No test cases found for this question"},
#                 status=status.HTTP_200_OK
#             )
        
#         # Get language from assignment
#         assignment = submission.assignment
#         if not assignment.language_data or not assignment.language_data.get('judge0_language_id'):
#             return Response(
#                 {"error": "Assignment has no Judge0 language ID specified"},
#                 status=status.HTTP_400_BAD_REQUEST
#             )
        
#         language_id = assignment.language_data['judge0_language_id']
#         code = submission.code
        
#         passed_count = 0
#         total_count = testcases.count()
        
#         # Evaluate each test case
#         for tc in testcases:
#             result = Judge0Service.evaluate_testcase(code, language_id, tc)
            
#             # Store result in database
#             TestCaseResult.objects.update_or_create(
#                 submission=submission,
#                 testcase=tc,
#                 defaults={
#                     "status": result["status"],
#                     "actual_output": result.get("actual_output", ""),
#                     "execution_time": result.get("execution_time"),
#                     "memory_used": result.get("memory_used"),
#                     "error_message": result.get("error_message", ""),
#                     "judge0_token": result.get("judge0_token", ""),
#                 }
#             )
            
#             if result["passed"]:
#                 passed_count += 1
        
#         # Calculate auto marks
#         question = submission.question
#         total_marks = question.total_marks
#         auto_marks = (passed_count / total_count) * total_marks if total_count > 0 else 0
        
#         # Update submission
#         submission.total_testcases = total_count
#         submission.passed_testcases = passed_count
#         submission.auto_marks = auto_marks
#         submission.save()
        
#         return Response({
#             "submission_id": submission.id,
#             "total_testcases": total_count,
#             "passed_testcases": passed_count,
#             "auto_marks": auto_marks,
#             "percentage": (passed_count / total_count * 100) if total_count > 0 else 0
#         })


# class SubmissionTestCaseResultsView(APIView):
#     """
#     Get test case results for a submission
#     GET /api/submission-testcase-results/{submission_id}/
#     """
#     permission_classes = [IsAuthenticated]
    
#     def get(self, request, submission_id):
#         try:
#             submission = Submission.objects.get(id=submission_id)
#         except Submission.DoesNotExist:
#             return Response(
#                 {"error": "Submission not found"},
#                 status=status.HTTP_404_NOT_FOUND
#             )
        
#         # Check permissions
#         user = request.user
#         try:
#             profile = user.profile
#         except:
#             return Response(
#                 {"error": "User profile not found"},
#                 status=status.HTTP_403_FORBIDDEN
#             )
        
#         # Students can only see their own submissions
#         if profile.role == 'student' and submission.student != user:
#             return Response(
#                 {"error": "Permission denied"},
#                 status=status.HTTP_403_FORBIDDEN
#             )
        
#         # Teachers can only see submissions for their assignments
#         if profile.role == 'teacher' and submission.assignment.teacher != user:
#             return Response(
#                 {"error": "Permission denied"},
#                 status=status.HTTP_403_FORBIDDEN
#             )
        
#         results = TestCaseResult.objects.filter(submission=submission)
#         serializer = TestCaseResultSerializer(results, many=True)
        
#         return Response({
#             "submission_id": submission.id,
#             "student": submission.student.username,
#             "student_name": submission.student.profile.name if hasattr(submission.student, 'profile') else submission.student.username,
#             "question": submission.question.title,
#             "code": submission.code,
#             "total_testcases": submission.total_testcases,
#             "passed_testcases": submission.passed_testcases,
#             "auto_marks": submission.auto_marks,
#             "custom_marks": submission.custom_marks,
#             "results": serializer.data
#         })


# class UpdateCustomMarksView(APIView):
#     """
#     Teacher endpoint to update custom marks
#     PATCH /api/update-custom-marks/{submission_id}/
#     Body: {"custom_marks": 8.5}
#     """
#     permission_classes = [IsAuthenticated]
    
#     def patch(self, request, submission_id):
#         try:
#             submission = Submission.objects.get(id=submission_id)
#         except Submission.DoesNotExist:
#             return Response(
#                 {"error": "Submission not found"},
#                 status=status.HTTP_404_NOT_FOUND
#             )
        
#         # Check if user is teacher and owns this assignment
#         user = request.user
#         try:
#             profile = user.profile
#         except:
#             return Response(
#                 {"error": "User profile not found"},
#                 status=status.HTTP_403_FORBIDDEN
#             )
        
#         if profile.role != 'teacher' or submission.assignment.teacher != user:
#             return Response(
#                 {"error": "Permission denied"},
#                 status=status.HTTP_403_FORBIDDEN
#             )
        
#         custom_marks = request.data.get('custom_marks')
        
#         if custom_marks is None:
#             return Response(
#                 {"error": "custom_marks is required"},
#                 status=status.HTTP_400_BAD_REQUEST
#             )
        
#         try:
#             submission.custom_marks = float(custom_marks)
#             submission.save()
#         except ValueError:
#             return Response(
#                 {"error": "custom_marks must be a number"},
#                 status=status.HTTP_400_BAD_REQUEST
#             )
        
#         return Response({
#             "submission_id": submission.id,
#             "auto_marks": submission.auto_marks,
#             "custom_marks": submission.custom_marks
#         })


# class AssignmentTestCaseSummaryView(APIView):
#     """
#     Get test case summary for all submissions of an assignment
#     GET /api/assignment-testcase-summary/{assignment_id}/
#     """
#     permission_classes = [IsAuthenticated]
    
#     def get(self, request, assignment_id):
#         try:
#             assignment = Assignment.objects.get(id=assignment_id)
#         except Assignment.DoesNotExist:
#             return Response(
#                 {"error": "Assignment not found"},
#                 status=status.HTTP_404_NOT_FOUND
#             )
        
#         # Check if user is teacher and owns this assignment
#         user = request.user
#         try:
#             profile = user.profile
#         except:
#             return Response(
#                 {"error": "User profile not found"},
#                 status=status.HTTP_403_FORBIDDEN
#             )
        
#         if profile.role != 'teacher' or assignment.teacher != user:
#             return Response(
#                 {"error": "Permission denied"},
#                 status=status.HTTP_403_FORBIDDEN
#             )
        
#         # Get all submissions for this assignment
#         submissions = Submission.objects.filter(assignment=assignment).select_related('student', 'question')
        
#         summary = []
#         for sub in submissions:
#             summary.append({
#                 "submission_id": sub.id,
#                 "student_id": sub.student.id,
#                 "student_name": sub.student.profile.name if hasattr(sub.student, 'profile') else sub.student.username,
#                 "question_id": sub.question.id,
#                 "question_title": sub.question.title,
#                 "total_testcases": sub.total_testcases,
#                 "passed_testcases": sub.passed_testcases,
#                 "auto_marks": sub.auto_marks,
#                 "custom_marks": sub.custom_marks,
#                 "status": sub.status,
#                 "submitted_at": sub.submitted_at
#             })
        
#         return Response({
#             "assignment_id": assignment.id,
#             "assignment_title": assignment.title,
#             "total_submissions": len(summary),
#             "submissions": summary
#         })






