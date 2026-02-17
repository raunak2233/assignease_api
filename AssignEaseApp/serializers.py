from rest_framework import serializers
from .models import Profile, Class, ClassStudent, ProgrammingLanguage, Assignment, Contact, AssignmentQuestion, Submission, TeacherFeedback, AssignmentAttachment, SubmissionFile, NonCodingSubmission, NonCodingSubmissionFile, TestCase, TestCaseResult, AIEvaluation
from django.contrib.auth.models import User
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)

        # Add custom claims
        try:
            profile = user.profile
            token['role'] = profile.role
        except Profile.DoesNotExist:
            token['role'] = None   

        return token
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'password']
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        # Create user
        user = User(
            username=validated_data['username'],
            email=validated_data['email'],
        )
        user.set_password(validated_data['password'])
        user.save()
        return user

class RegistrationSerializer(serializers.ModelSerializer):
    role = serializers.ChoiceField(choices=Profile.USER_ROLES)
    name = serializers.CharField(max_length=255)
    enrollment_number = serializers.CharField(max_length=50, required=False, allow_blank=True)
    tid = serializers.CharField(max_length=50, required=False, allow_blank=True)
    contact_number = serializers.CharField(max_length=15, required=False, allow_blank=True)
    college = serializers.CharField(max_length=255, required=False, allow_blank=True)
    course = serializers.CharField(max_length=100, required=False, allow_blank=True)
    year = serializers.IntegerField(required=False, allow_null=True)
    batch = serializers.CharField(max_length=20, required=False, allow_blank=True)

    class Meta:
        model = User
        fields = [
            'username', 'email', 'password', 'role', 'name', 
            'enrollment_number', 'tid', 'contact_number', 
            'college', 'course', 'year', 'batch'
        ]
        extra_kwargs = {'password': {'write_only': True}}

    def validate(self, data):
        username = data.get('username')
        if User.objects.filter(username=username).exists():
            raise serializers.ValidationError({
                "username": "A user with this username already exists."
            })

        email = data.get('email')
        if User.objects.filter(email=email).exists():
            raise serializers.ValidationError({
                "email": "A user with this email already exists."
            })

        return data

    def create(self, validated_data): 
        role = validated_data.pop('role')
        name = validated_data.pop('name')
        enrollment_number = validated_data.pop('enrollment_number', None)
        tid = validated_data.pop('tid', None)
        contact_number = validated_data.pop('contact_number', None)
        college = validated_data.pop('college', None)
        course = validated_data.pop('course', None)
        year = validated_data.pop('year', None)
        batch = validated_data.pop('batch', None)

        user = User(
            username=validated_data['username'],
            email=validated_data['email'],
        )
        user.set_password(validated_data['password'])
        user.save()

        Profile.objects.create(
            user=user,
            role=role,
            name=name,
            enrollment_number=enrollment_number,
            tid=tid,
            contact_number=contact_number,
            college=college,
            course=course,
            year=year,
            batch=batch,
        )

        return user

class ProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    email = serializers.CharField(source='user.email', read_only=True)
    avatar_url = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Profile
        fields = [
            'id', 'user', 'username', 'email', 'role', 'name', 
            'enrollment_number', 'tid', 'contact_number', 'avatar', 
            'avatar_url', 'college', 'course', 'year', 'batch', 
            'bio', 'date_of_birth', 'address'
        ]
        read_only_fields = ['user', 'username', 'email', 'avatar_url']

    def get_avatar_url(self, obj):
        if obj.avatar:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.avatar.url)
            return obj.avatar.url
        return None

    def validate_contact_number(self, value):
        if value and not value.replace('+', '').replace('-', '').replace(' ', '').isdigit():
            raise serializers.ValidationError("Invalid contact number format")
        return value

    def validate_year(self, value):
        if value and (value < 1 or value > 10):
            raise serializers.ValidationError("Year must be between 1 and 10")
        return value


class ClassSerializer(serializers.ModelSerializer):
    teacher = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), required=False)

    class Meta:
        model = Class
        fields = ['id', 'class_name', 'teacher', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']

    def create(self, validated_data):
        if 'teacher' not in validated_data:
            validated_data['teacher'] = self.context['request'].user
        return super().create(validated_data)

class ClassStudentSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="student.profile.name", read_only=True)
    enrollment_number = serializers.CharField(source="student.profile.enrollment_number", read_only=True)
    class_name = serializers.CharField(source="class_assigned.class_name", read_only=True)
    class_assigned = serializers.PrimaryKeyRelatedField(queryset=Class.objects.all(), write_only=True)

    class Meta: 
        model = ClassStudent
        fields = ['id', 'student', 'class_assigned', 'class_name', 'student_name', 'enrollment_number']

    def validate(self, data):
        student = data.get('student')
        class_assigned = data.get('class_assigned')
        if ClassStudent.objects.filter(student=student, class_assigned=class_assigned).exists():
            raise serializers.ValidationError("This student is already assigned to this class.")
        return data


class ClassStudentDetailSerializer(serializers.ModelSerializer):
    class_assigned = serializers.StringRelatedField()

    class Meta:
        model = ClassStudent
        fields = ['id', 'student', 'class_assigned']

class ProgrammingLanguageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProgrammingLanguage
        fields = [
            'id', 'display_name', 'piston_name', 'piston_version',
            'judge0_language_id', 'judge0_language_name', 'is_active',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']

# TestCase Serializers (must be before AssignmentQuestionSerializer)
class TestCaseSerializer(serializers.ModelSerializer):
    question = serializers.PrimaryKeyRelatedField(queryset=AssignmentQuestion.objects.all())
    input = serializers.CharField(required=False, allow_blank=True, default='')
    expected_output = serializers.CharField(required=False, allow_blank=True, default='')

    class Meta:
        model = TestCase
        fields = ['id', 'question', 'input', 'expected_output', 'marks', 'visibility', 'timeout', 'memory_limit']

    def validate(self, data):
        question = data.get('question')
        if question and question.assignment.assignment_type != 'coding':
            raise ValidationError({"question": "Test cases can only be added to coding assignment questions."})
        return data

    def create(self, validated_data):
        return TestCase.objects.create(**validated_data)


class TestCaseResultSerializer(serializers.ModelSerializer):
    testcase_input = serializers.CharField(source='testcase.input', read_only=True)
    testcase_expected_output = serializers.CharField(source='testcase.expected_output', read_only=True)
    testcase_marks = serializers.IntegerField(source='testcase.marks', read_only=True)
    testcase_visibility = serializers.CharField(source='testcase.visibility', read_only=True)
    assignment_id = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = TestCaseResult
        fields = [
            'id', 'testcase', 'status', 'actual_output', 
            'execution_time', 'memory_used', 'error_message',
            'testcase_input', 'testcase_expected_output', 
            'testcase_marks', 'testcase_visibility', 'assignment_id', 'created_at'
        ]
        read_only_fields = ['created_at']

    def get_assignment_id(self, obj):
        try:
            return obj.submission.assignment.id
        except Exception:
            return None

 
class AssignmentQuestionSerializer(serializers.ModelSerializer):
    testcases = serializers.SerializerMethodField()
    
    class Meta:
        model = AssignmentQuestion
        fields = ['id', 'title', 'assignment', 'total_marks', 'testcases', 'created_at']
    
    def get_testcases(self, obj):
        # Only return public testcases for students, all for teachers
        request = self.context.get('request')
        if request and hasattr(request.user, 'profile'):
            if request.user.profile.role == 'student':
                testcases = obj.testcases.filter(visibility='public')
            else:
                testcases = obj.testcases.all()
        else:
            testcases = obj.testcases.filter(visibility='public')
        
        return TestCaseSerializer(testcases, many=True).data

class AssignmentSerializer(serializers.ModelSerializer):
    due_date = serializers.DateField(input_formats=['%Y-%m-%d', '%d/%m/%Y', '%m-%d-%Y'])
    class_name = serializers.CharField(source='class_assigned.class_name', read_only=True)
    questions = AssignmentQuestionSerializer(many=True, read_only=True, source='assignmentquestion_set')
    is_submitted = serializers.SerializerMethodField()
    attachments = serializers.SerializerMethodField()
    assignment_type = serializers.ChoiceField(choices=Assignment.ASSIGNMENT_TYPE_CHOICES, required=False)
    submission_type = serializers.ChoiceField(choices=Assignment.SUBMISSION_TYPE_CHOICES, required=False)
    assignment_type_display = serializers.CharField(source='get_assignment_type_display', read_only=True)
    submission_type_display = serializers.CharField(source='get_submission_type_display', read_only=True)
    language = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    language_version = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    
    class Meta:
        model = Assignment
        fields = [
            'id','title','description','due_date','class_name','questions',
            'class_assigned','teacher','language','language_version',
            'assignment_type','assignment_type_display',
            'submission_type','submission_type_display',
            'is_submitted','attachments'
        ]

    def get_is_submitted(self, obj):
        student_id = self.context.get('student_id', None)
        if not student_id:
            return False  
        
        return Submission.objects.filter(assignment=obj, student_id=student_id).exists()
    
    def get_attachments(self, obj):
        request = self.context.get('request')
        if obj.attachments and request:
            return [request.build_absolute_uri(att.file.url) for att in obj.attachments.all()]
        return []


class SubmissionSerializer(serializers.ModelSerializer):
    title = serializers.CharField(source="assignment.title", read_only=True)
    subject = serializers.CharField(source="assignment.class_assigned.class_name", read_only=True)
    assignment = serializers.PrimaryKeyRelatedField(queryset=Assignment.objects.all())
    student = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), required=False)
    student_info = serializers.SerializerMethodField(read_only=True)
    question = serializers.PrimaryKeyRelatedField(queryset=AssignmentQuestion.objects.all())
    questiontext = serializers.CharField(source="question.title", read_only=True)
    # new fields
    text_submission = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    files = serializers.ListField(
        child=serializers.FileField(max_length=None, allow_empty_file=False, use_url=False),
        write_only=True,
        required=False
    )
    files_info = serializers.SerializerMethodField()
    
    # Test case related fields
    testcase_results = TestCaseResultSerializer(many=True, read_only=True)
    auto_marks = serializers.FloatField(read_only=True)
    custom_marks = serializers.FloatField(required=False, allow_null=True)
    total_testcases = serializers.IntegerField(read_only=True)
    passed_testcases = serializers.IntegerField(read_only=True)

    class Meta:
        model = Submission
        fields = [
            'id', 'title', 'subject', 'assignment', 'student', 'student_info', 
            'question', 'questiontext', 'code', 'text_submission', 'files', 'files_info', 
            'status', 'feedback', 'submitted_at', 'updated_at',
            'testcase_results', 'auto_marks', 'custom_marks', 'total_testcases', 'passed_testcases'
        ]
        read_only_fields = ['submitted_at', 'updated_at', 'auto_marks', 'total_testcases', 'passed_testcases']

    def get_files_info(self, obj):
        request = self.context.get('request')
        if obj.files and request:
            return [request.build_absolute_uri(file.file.url) for file in obj.files.all()]
        return []

    def get_student_info(self, obj):
        if obj.student:
            try:
                profile = obj.student.profile
                return {
                    'id': obj.student.id,
                    'username': obj.student.username,
                    'name': profile.name,
                    'enrollment_number': profile.enrollment_number,
                    'email': obj.student.email
                }
            except Profile.DoesNotExist:
                return {
                    'id': obj.student.id,
                    'username': obj.student.username,
                    'name': None,
                    'enrollment_number': None,
                    'email': obj.student.email
                }
        return None

    def validate_files(self, value):
        # Validate each file's extension and size (default constraints applied by model validators too)
        allowed_ext = ['jpg','jpeg','png','xlsx','xls','csv','pdf','doc','docx']
        max_mb = 10
        for f in value:
            ext = f.name.split('.')[-1].lower()
            if ext not in allowed_ext:
                raise serializers.ValidationError(f"File type .{ext} is not allowed.")
            if f.size > max_mb * 1024 * 1024:
                raise serializers.ValidationError(f"Maximum file size is {max_mb} MB.")
        return value

    def create(self, validated_data):
        request = self.context.get('request')
        files = validated_data.pop('files', None)
        if 'student' not in validated_data:
            validated_data['student'] = request.user if request else None

        # Create submission record
        submission = Submission.objects.create(**validated_data)

        # Handle uploaded files (if any)
        if files:
            for f in files:
                SubmissionFile.objects.create(submission=submission, file=f)

        return submission


class TeacherFeedbackSerializer(serializers.ModelSerializer):
    submission = serializers.PrimaryKeyRelatedField(queryset=Submission.objects.all())
    teacher = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), required=False)

    class Meta:
        model = TeacherFeedback
        fields = ['id', 'submission', 'teacher', 'feedback', 'resubmission_requested', 'created_at']
        read_only_fields = ['created_at']

    def create(self, validated_data):
        if 'teacher' not in validated_data:
            validated_data['teacher'] = self.context['request'].user
        return super().create(validated_data)

class AssignmentAttachmentSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = AssignmentAttachment
        fields = ['id', 'assignment', 'file', 'file_url', 'uploaded_at']
        read_only_fields = ['file_url', 'uploaded_at']

    def get_file_url(self, obj):
        request = self.context.get('request')
        if obj.file and request:
            return request.build_absolute_uri(obj.file.url)
        if obj.file:
            return obj.file.url
        return None

# New serializers for non-coding submissions

class NonCodingSubmissionFileSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = NonCodingSubmissionFile
        fields = ['id', 'file', 'file_url', 'uploaded_at']
        read_only_fields = ['file_url', 'uploaded_at']

    def get_file_url(self, obj):
        request = self.context.get('request')
        if obj.file and request:
            return request.build_absolute_uri(obj.file.url)
        if obj.file:
            return obj.file.url
        return None


class NonCodingSubmissionSerializer(serializers.ModelSerializer):
    assignment = serializers.PrimaryKeyRelatedField(queryset=Assignment.objects.all())
    student = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), required=False)
    student_info = serializers.SerializerMethodField(read_only=True)
    text_submission = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    files = serializers.ListField(
        child=serializers.FileField(max_length=None, allow_empty_file=False, use_url=False),
        write_only=True,
        required=False
    )
    files_info = NonCodingSubmissionFileSerializer(many=True, read_only=True, source='files')

    class Meta:
        model = NonCodingSubmission
        fields = ['id', 'assignment', 'student', 'student_info', 'text_submission', 'files', 'files_info', 'status', 'feedback', 'submitted_at', 'updated_at']
        read_only_fields = ['submitted_at', 'updated_at']

    def validate(self, data):
        assignment = data.get('assignment')
        if not assignment:
            raise serializers.ValidationError({"assignment": "This field is required."})

        # Ensure assignment is non-coding
        if assignment.assignment_type != 'non_coding':
            raise serializers.ValidationError({"assignment": "This assignment is not a non-coding assignment."})

        # Skip content validation during updates if we're only updating status/feedback
        # This allows teachers to update status without requiring content
        is_update = self.instance is not None
        updating_only_status_feedback = is_update and set(data.keys()).issubset({'assignment', 'status', 'feedback'})
        
        if not updating_only_status_feedback:
            stype = assignment.submission_type
            text = data.get('text_submission', None)
            files = data.get('files', None)

            # For updates, check existing content if new content is not provided
            if is_update and self.instance:
                existing_text = self.instance.text_submission
                existing_files = self.instance.files.exists()
                
                # Use existing content if not provided in update
                if text is None and existing_text:
                    text = existing_text
                if not files and existing_files:
                    files = True  # Just to pass the validation

            # Enforce submission_type rules only for creation or content updates
            if stype == 'text_only' and not text:
                raise serializers.ValidationError({"text_submission": "This assignment requires a text submission."})
            if stype == 'files_only' and not files:
                raise serializers.ValidationError({"files": "This assignment requires file upload(s)."})
            if stype == 'text_and_files' and not (text or files):
                raise serializers.ValidationError("This assignment requires text and/or files.")

        # Validate files if provided
        files = data.get('files', None)
        if files:
            allowed = assignment.allowed_file_formats or ['jpg','jpeg','png','xlsx','xls','csv','pdf','doc','docx']
            max_mb = assignment.max_file_size_mb or 10
            if len(files) > assignment.max_files_per_submission:
                raise serializers.ValidationError({"files": f"Maximum {assignment.max_files_per_submission} files allowed."})
            for f in files:
                ext = f.name.split('.')[-1].lower()
                if allowed and ext not in allowed:
                    raise serializers.ValidationError({"files": f"File type .{ext} is not allowed."})
                if f.size > max_mb * 1024 * 1024:
                    raise serializers.ValidationError({"files": f"Maximum file size is {max_mb} MB."})

        return data

    def create(self, validated_data):
        request = self.context.get('request')
        files = validated_data.pop('files', None)
        if 'student' not in validated_data or validated_data.get('student') is None:
            validated_data['student'] = request.user if request else None

        # Create non-coding submission
        submission = NonCodingSubmission.objects.create(**validated_data)

        # Attach files if any
        if files:
            for f in files:
                NonCodingSubmissionFile.objects.create(submission=submission, file=f)

        return submission

    def update(self, instance, validated_data):
        request = self.context.get('request')
        files = validated_data.pop('files', None)
        
        # Update the instance with validated data
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Handle new files if provided (append to existing files)
        if files:
            for f in files:
                NonCodingSubmissionFile.objects.create(submission=instance, file=f)

        return instance

    def get_student_info(self, obj):
        if obj.student:
            try:
                profile = obj.student.profile
                return {
                    'id': obj.student.id,
                    'username': obj.student.username,
                    'name': profile.name,
                    'enrollment_number': profile.enrollment_number,
                    'email': obj.student.email
                }
            except Profile.DoesNotExist:
                return {
                    'id': obj.student.id,
                    'username': obj.student.username,
                    'name': None,
                    'enrollment_number': None,
                    'email': obj.student.email
                }
        return None

# New serializer for TestCase
class TestCaseSerializer(serializers.ModelSerializer):
    question = serializers.PrimaryKeyRelatedField(queryset=AssignmentQuestion.objects.all())

    class Meta:
        model = TestCase
        fields = ['id', 'question', 'input', 'expected_output', 'marks', 'visibility', 'timeout', 'memory_limit']

    def validate(self, data):
        question = data.get('question')
        if question and question.assignment.assignment_type != 'coding':
            raise ValidationError({"question": "Test cases can only be added to coding assignment questions."})
        return data

    def create(self, validated_data):
        return TestCase.objects.create(**validated_data)


# TestCase and TestCaseResult Serializers
class TestCaseResultSerializer(serializers.ModelSerializer):
    testcase_input = serializers.CharField(source='testcase.input', read_only=True)
    testcase_expected_output = serializers.CharField(source='testcase.expected_output', read_only=True)
    testcase_marks = serializers.IntegerField(source='testcase.marks', read_only=True)
    testcase_visibility = serializers.CharField(source='testcase.visibility', read_only=True)
    assignment_id = serializers.SerializerMethodField(read_only=True)
    
    class Meta:
        model = TestCaseResult
        fields = [
            'id', 'testcase', 'status', 'actual_output', 
            'execution_time', 'memory_used', 'error_message',
            'testcase_input', 'testcase_expected_output', 
            'testcase_marks', 'testcase_visibility', 'assignment_id', 'created_at'
        ]
        read_only_fields = ['created_at']

    def get_assignment_id(self, obj):
        try:
            return obj.submission.assignment.id
        except Exception:
            return None

class ContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contact
        fields = ['id', 'name', 'phone', 'email', 'message', 'created_at']
        read_only_fields = ['id', 'created_at']


class AIEvaluationSerializer(serializers.ModelSerializer):
    student_info = serializers.SerializerMethodField(read_only=True)
    assignment_title = serializers.CharField(source='assignment.title', read_only=True)
    submission_id = serializers.IntegerField(source='submission.id', read_only=True)

    class Meta:
        model = AIEvaluation
        fields = [
            'id', 'submission_id', 'assignment', 'assignment_title', 'question', 'student', 'student_info',
            'question_text', 'student_answer', 'mistake_type', 'ai_score', 'confidence', 'feedback',
            'raw_response', 'model_name', 'status', 'error', 'created_at', 'completed_at'
        ]

    def get_student_info(self, obj):
        if obj.student:
            try:
                profile = obj.student.profile
                return {
                    'id': obj.student.id,
                    'username': obj.student.username,
                    'name': profile.name,
                    'email': obj.student.email,
                }
            except Profile.DoesNotExist:
                return {
                    'id': obj.student.id,
                    'username': obj.student.username,
                    'name': None,
                    'email': obj.student.email,
                }
        return None