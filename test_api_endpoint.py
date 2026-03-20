#!/usr/bin/env python
"""
Test the API endpoint for generating database assignments with AI
"""
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'AssignEaseApi.settings')
import django
django.setup()

import json
import requests

# Test data
payload = {
    "questions": [
        "Create a student database with names and roll numbers",
        "Write a query to find all students with roll number > 50"
    ]
}

API_URL = "https://api.assignease.io/api/generate-database-assignment-ai/"

print("="*60)
print("Testing AI Database Assignment Generation API")
print("="*60)

print(f"\nSending POST request to {API_URL}")
print(f"Payload: {json.dumps(payload, indent=2)}")
print("\nWaiting for response (120 seconds timeout)...\n")

try:
    response = requests.post(
        API_URL,
        json=payload,
        timeout=150,
        headers={"X-CSRFToken": "test"}  # CSRF not needed for API test
    )
    
    print(f"Status Code: {response.status_code}")
    print("-" * 60)
    
    if response.status_code == 200:
        result = response.json()
        print("✓ SUCCESS!\n")
        print(f"Response keys: {list(result.keys())}")
        
        if 'schema_sql' in result:
            print(f"\nSchema SQL ({len(result['schema_sql'])} chars):")
            print(result['schema_sql'][:200] + "..." if len(result['schema_sql']) > 200 else result['schema_sql'])
        
        if 'sample_data_sql' in result:
            print(f"\nSample Data SQL ({len(result['sample_data_sql'])} chars):")
            print(result['sample_data_sql'][:200] + "..." if len(result['sample_data_sql']) > 200 else result['sample_data_sql'])
        
        if 'questions' in result:
            questions = result['questions']
            print(f"\nGenerated {len(questions)} questions:")
            for i, q in enumerate(questions[:3], 1):
                print(f"\n  Q{i}: {q.get('question_text', 'N/A')[:60]}...")
                print(f"       Type: {q.get('question_type', 'N/A')}")
                print(f"       Query: {q.get('expected_query', 'N/A')[:50]}...")
    else:
        print(f"✗ Error {response.status_code}\n")
        print("Response:")
        try:
            print(json.dumps(response.json(), indent=2))
        except:
            print(response.text[:500])
    
    print("\n" + "="*60)
    
except Exception as e:
    print(f"✗ Request failed: {type(e).__name__}: {str(e)}")
    print("="*60)
    print("\nNote: Make sure Django server is running:")
    print("  python manage.py runserver")
