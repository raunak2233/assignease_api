#!/usr/bin/env python
"""
Setup test user and test AI API endpoint with authentication
"""
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'AssignEaseApi.settings')
import django
django.setup()

from django.contrib.auth.models import User
from rest_framework_simplejwt.tokens import RefreshToken
from AssignEaseApp.models import Profile
import json
import requests

# Create or get test teacher user
print("Setting up test user...")
username = "test_teacher_ai"
email = "test_teacher_ai@example.com"
password = "testpass123"

user, created = User.objects.get_or_create(
    username=username,
    defaults={
        'email': email,
        'first_name': 'Test',
        'last_name': 'Teacher'
    }
)

if created:
    user.set_password(password)
    user.save()
    print(f"✓ Created new user: {username}")
else:
    print(f"✓ Using existing user: {username}")
    # Update password just in case
    user.set_password(password)
    user.save()

# Ensure user has teacher profile
profile, profile_created = Profile.objects.get_or_create(
    user=user,
    defaults={'role': 'teacher', 'college': 'Test School'}
)
if profile_created:
    print(f"✓ Created teacher profile")
else:
    if profile.role != 'teacher':
        profile.role = 'teacher'
        profile.save()
        print(f"✓ Updated profile to teacher role")
    else:
        print(f"✓ Profile is already teacher")

# Get JWT token for authentication
refresh = RefreshToken.for_user(user)
access_token = str(refresh.access_token)
print(f"\n✓ Generated JWT access token")
print(f"Token: {access_token[:30]}...")

# Now test the API
print("\n" + "="*60)
print("Testing AI Database Assignment Generation API")
print("="*60)

API_URL = "http://127.0.0.1:8000/api/generate-database-assignment-ai/"
payload = {
    "questions": [
        "Create a student database with names and roll numbers",
        "Write a query to find all students with roll number > 50"
    ]
}

headers = {
    "Authorization": f"Bearer {access_token}",
    "Content-Type": "application/json"
}

print(f"\nSending POST request to {API_URL}")
print(f"Payload: {json.dumps(payload, indent=2)}\n")

try:
    response = requests.post(
        API_URL,
        json=payload,
        headers=headers,
        timeout=150
    )
    
    print(f"Status Code: {response.status_code}")
    print("-" * 60)
    
    if response.status_code == 200:
        result = response.json()
        print("✓ SUCCESS!\n")
        print(f"Response keys: {list(result.keys())}")
        
        if 'schema_sql' in result:
            print(f"\nSchema SQL ({len(result['schema_sql'])} chars):")
            schema_preview = result['schema_sql'][:150]
            print(schema_preview + ("..." if len(result['schema_sql']) > 150 else ""))
        
        if 'sample_data_sql' in result:
            print(f"\nSample Data SQL ({len(result['sample_data_sql'])} chars):")
            sample_preview = result['sample_data_sql'][:150]
            print(sample_preview + ("..." if len(result['sample_data_sql']) > 150 else ""))
        
        if 'questions' in result:
            questions = result['questions']
            print(f"\nGenerated {len(questions)} questions:")
            for i, q in enumerate(questions[:3], 1):
                q_text = q.get('question_text', 'N/A')[:60]
                q_type = q.get('question_type', 'N/A')
                q_query = q.get('expected_query', 'N/A')[:50]
                print(f"  Q{i}: {q_text}...")
                print(f"       Type: {q_type} | Query: {q_query}...")
    else:
        print(f"✗ Error {response.status_code}\n")
        print("Response:")
        try:
            error_data = response.json()
            print(json.dumps(error_data, indent=2))
        except:
            print(response.text[:500])
    
    print("\n" + "="*60 + "\n")
    
except Exception as e:
    print(f"✗ Request failed: {type(e).__name__}: {str(e)}")
    print("\nNote: Make sure Django server is running on http://127.0.0.1:8000")
