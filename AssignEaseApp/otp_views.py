import random
import string
from datetime import datetime, timedelta
from django.core.mail import send_mail
from django.conf import settings
from django.core.cache import cache
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth.models import User
from .models import Profile
from rest_framework_simplejwt.tokens import RefreshToken


class SendOTPView(APIView):
    """
    Send OTP to email for verification
    POST /api/otp/send/
    Body: { "email": "user@example.com", "purpose": "registration" or "login" or "password_reset" }
    """
    permission_classes = []

    def generate_otp(self, length=6):
        """Generate a random OTP"""
        return ''.join(random.choices(string.digits, k=length))

    def post(self, request):
        email = request.data.get('email')
        purpose = request.data.get('purpose', 'verification')  # registration, login, password_reset
        
        if not email:
            return Response(
                {'error': 'Email is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validate email format
        if '@' not in email or '.' not in email:
            return Response(
                {'error': 'Invalid email format'},
                status=status.HTTP_400_BAD_REQUEST
            )

        user_exists = User.objects.filter(email=email).exists()
        
        if purpose == 'registration' and user_exists:
            return Response(
                {'error': 'Email already registered'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if purpose in ['login', 'password_reset'] and not user_exists:
            return Response(
                {'error': 'Email not registered'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Generate OTP
        otp = self.generate_otp()
        
        # Store OTP in cache with 5 minutes expiry
        cache_key = f'otp_{email}_{purpose}'
        cache.set(cache_key, otp, timeout=300)  # 5 minutes
        
        # Store attempt count to prevent spam
        attempt_key = f'otp_attempts_{email}'
        attempts = cache.get(attempt_key, 0)
        
        if attempts >= 5:
            return Response(
                {'error': 'Too many OTP requests. Please try again later.'},
                status=status.HTTP_429_TOO_MANY_REQUESTS
            )
        
        cache.set(attempt_key, attempts + 1, timeout=3600)  # Reset after 1 hour

        # Send OTP via email
        try:
            subject = self.get_email_subject(purpose)
            message = self.get_email_message(otp, purpose)
            
            send_mail(
                subject,
                message,
                settings.EMAIL_HOST_USER,
                [email],
                fail_silently=False,
            )
            
            return Response({
                'message': 'OTP sent successfully',
                'email': email,
                'expires_in': 300  # seconds
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response(
                {'error': f'Failed to send email: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def get_email_subject(self, purpose):
        subjects = {
            'registration': 'AssignEase - Verify Your Email',
            'login': 'AssignEase - Login Verification Code',
            'password_reset': 'AssignEase - Password Reset Code'
        }
        return subjects.get(purpose, 'AssignEase - Verification Code')

    def get_email_message(self, otp, purpose):
        messages = {
            'registration': f'''
Hello,

Thank you for registering with AssignEase!

Your verification code is: {otp}

This code will expire in 5 minutes.

If you didn't request this code, please ignore this email.

Best regards,
AssignEase Team
            ''',
            'login': f'''
Hello,

Your login verification code is: {otp}

This code will expire in 5 minutes.

If you didn't request this code, please secure your account immediately.

Best regards,
AssignEase Team
            ''',
            'password_reset': f'''
Hello,

Your password reset code is: {otp}

This code will expire in 5 minutes.

If you didn't request this code, please ignore this email.

Best regards,
AssignEase Team
            '''
        }
        return messages.get(purpose, f'Your verification code is: {otp}')


class VerifyOTPView(APIView):
    """
    Verify OTP
    POST /api/otp/verify/
    Body: { 
        "email": "user@example.com", 
        "otp": "123456",
        "purpose": "registration",
        "user_data": {  // Required only for registration
            "username": "john_doe",
            "password": "secure_password",
            "role": "student",
            "name": "John Doe"
        }
    }
    """
    permission_classes = []

    def post(self, request):
        email = request.data.get('email')
        otp = request.data.get('otp')
        purpose = request.data.get('purpose', 'verification')
        
        if not email or not otp:
            return Response(
                {'error': 'Email and OTP are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get OTP from cache
        cache_key = f'otp_{email}_{purpose}'
        stored_otp = cache.get(cache_key)
        
        if not stored_otp:
            return Response(
                {'error': 'OTP expired or not found. Please request a new one.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Verify OTP
        if stored_otp != otp:
            return Response(
                {'error': 'Invalid OTP'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # OTP is valid, delete it from cache
        cache.delete(cache_key)
        
        # Handle different purposes
        if purpose == 'registration':
            return self.handle_registration(request, email)
        elif purpose == 'login':
            return self.handle_login(email)
        elif purpose == 'password_reset':
            return self.handle_password_reset_verification(email)
        
        return Response({
            'message': 'OTP verified successfully',
            'email': email
        }, status=status.HTTP_200_OK)

    def handle_registration(self, request, email):
        """Create user account after OTP verification"""
        user_data = request.data.get('user_data', {})
        
        username = user_data.get('username')
        password = user_data.get('password')
        role = user_data.get('role', 'student')
        name = user_data.get('name')
        enrollment_number = user_data.get('enrollment_number')
        tid = user_data.get('tid')
        
        if not username or not password:
            return Response(
                {'error': 'Username and password are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check if username already exists
        if User.objects.filter(username=username).exists():
            return Response(
                {'error': 'Username already exists'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Create user
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password
            )
            
            # Create profile
            Profile.objects.create(
                user=user,
                role=role,
                name=name,
                enrollment_number=enrollment_number,
                tid=tid
            )
            
            # Generate JWT tokens
            refresh = RefreshToken.for_user(user)
            refresh['role'] = role
            
            return Response({
                'message': 'Registration successful',
                'access': str(refresh.access_token),
                'refresh': str(refresh),
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'name': name,
                    'role': role
                }
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response(
                {'error': f'Registration failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def handle_login(self, email):
        """Login user after OTP verification"""
        try:
            user = User.objects.get(email=email)
            profile = user.profile
            
            # Generate JWT tokens
            refresh = RefreshToken.for_user(user)
            refresh['role'] = profile.role
            
            return Response({
                'message': 'Login successful',
                'access': str(refresh.access_token),
                'refresh': str(refresh),
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'name': profile.name,
                    'role': profile.role
                }
            }, status=status.HTTP_200_OK)
            
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )

    def handle_password_reset_verification(self, email):
        """Verify OTP for password reset"""
        # Generate a temporary token for password reset
        reset_token = ''.join(random.choices(string.ascii_letters + string.digits, k=32))
        
        # Store reset token in cache for 15 minutes
        cache.set(f'password_reset_{email}', reset_token, timeout=900)
        
        return Response({
            'message': 'OTP verified. You can now reset your password.',
            'reset_token': reset_token,
            'email': email
        }, status=status.HTTP_200_OK)


class ResetPasswordView(APIView):
    """
    Reset password using verified token
    POST /api/otp/reset-password/
    Body: { 
        "email": "user@example.com",
        "reset_token": "token_from_verification",
        "new_password": "new_secure_password"
    }
    """
    permission_classes = []

    def post(self, request):
        email = request.data.get('email')
        reset_token = request.data.get('reset_token')
        new_password = request.data.get('new_password')
        
        if not email or not reset_token or not new_password:
            return Response(
                {'error': 'Email, reset token, and new password are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Verify reset token
        stored_token = cache.get(f'password_reset_{email}')
        
        if not stored_token or stored_token != reset_token:
            return Response(
                {'error': 'Invalid or expired reset token'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            user = User.objects.get(email=email)
            user.set_password(new_password)
            user.save()
            
            # Delete reset token
            cache.delete(f'password_reset_{email}')
            
            return Response({
                'message': 'Password reset successful. You can now login with your new password.'
            }, status=status.HTTP_200_OK)
            
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )
