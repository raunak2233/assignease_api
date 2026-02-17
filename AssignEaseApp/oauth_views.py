import requests
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth.models import User
from django.conf import settings
from .models import Profile
from rest_framework_simplejwt.tokens import RefreshToken


class GoogleOAuthView(APIView):
    """
    Google OAuth Login/Signup
    POST /api/auth/google/
    Body: { "access_token": "google_access_token" }
    """
    permission_classes = []

    def post(self, request):
        access_token = request.data.get('access_token')
        
        if not access_token:
            return Response(
                {'error': 'Access token is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Verify token with Google
            google_response = requests.get(
                'https://www.googleapis.com/oauth2/v3/userinfo',
                headers={'Authorization': f'Bearer {access_token}'}
            )

            if google_response.status_code != 200:
                return Response(
                    {'error': 'Invalid access token'},
                    status=status.HTTP_401_UNAUTHORIZED
                )

            user_data = google_response.json()
            email = user_data.get('email')
            name = user_data.get('name')
            google_id = user_data.get('sub')

            if not email:
                return Response(
                    {'error': 'Email not provided by Google'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Check if user exists
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    'username': email.split('@')[0] + '_' + google_id[:8],
                    'first_name': name.split()[0] if name else '',
                    'last_name': ' '.join(name.split()[1:]) if name and len(name.split()) > 1 else ''
                }
            )

            # Create or get profile
            profile, profile_created = Profile.objects.get_or_create(
                user=user,
                defaults={
                    'role': request.data.get('role', 'student'),  # Default to student
                    'name': name
                }
            )

            # Generate JWT tokens
            refresh = RefreshToken.for_user(user)
            refresh['role'] = profile.role

            return Response({
                'access': str(refresh.access_token),
                'refresh': str(refresh),
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'name': profile.name,
                    'role': profile.role
                },
                'is_new_user': created
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class GitHubOAuthView(APIView):
    """
    GitHub OAuth Login/Signup
    POST /api/auth/github/
    Body: { "code": "github_authorization_code" }
    """
    permission_classes = []

    def post(self, request):
        code = request.data.get('code')
        
        if not code:
            return Response(
                {'error': 'Authorization code is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Exchange code for access token
            token_response = requests.post(
                'https://github.com/login/oauth/access_token',
                data={
                    'client_id': settings.GITHUB_CLIENT_ID,
                    'client_secret': settings.GITHUB_CLIENT_SECRET,
                    'code': code
                },
                headers={'Accept': 'application/json'}
            )

            if token_response.status_code != 200:
                return Response(
                    {'error': 'Failed to exchange code for token'},
                    status=status.HTTP_401_UNAUTHORIZED
                )

            token_data = token_response.json()
            access_token = token_data.get('access_token')

            if not access_token:
                return Response(
                    {'error': 'Access token not received from GitHub'},
                    status=status.HTTP_401_UNAUTHORIZED
                )

            # Get user info from GitHub
            user_response = requests.get(
                'https://api.github.com/user',
                headers={'Authorization': f'Bearer {access_token}'}
            )

            if user_response.status_code != 200:
                return Response(
                    {'error': 'Failed to get user info from GitHub'},
                    status=status.HTTP_401_UNAUTHORIZED
                )

            user_data = user_response.json()
            github_id = user_data.get('id')
            username = user_data.get('login')
            name = user_data.get('name') or username
            email = user_data.get('email')

            # If email is not public, fetch from emails endpoint
            if not email:
                emails_response = requests.get(
                    'https://api.github.com/user/emails',
                    headers={'Authorization': f'Bearer {access_token}'}
                )
                if emails_response.status_code == 200:
                    emails = emails_response.json()
                    primary_email = next((e for e in emails if e.get('primary')), None)
                    if primary_email:
                        email = primary_email.get('email')

            if not email:
                return Response(
                    {'error': 'Email not provided by GitHub. Please make your email public.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Check if user exists
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    'username': username + '_gh' + str(github_id)[:6],
                    'first_name': name.split()[0] if name else '',
                    'last_name': ' '.join(name.split()[1:]) if name and len(name.split()) > 1 else ''
                }
            )

            # Create or get profile
            profile, profile_created = Profile.objects.get_or_create(
                user=user,
                defaults={
                    'role': request.data.get('role', 'student'),  # Default to student
                    'name': name
                }
            )

            # Generate JWT tokens
            refresh = RefreshToken.for_user(user)
            refresh['role'] = profile.role

            return Response({
                'access': str(refresh.access_token),
                'refresh': str(refresh),
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'name': profile.name,
                    'role': profile.role
                },
                'is_new_user': created
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
