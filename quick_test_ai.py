#!/usr/bin/env python
"""Quick test of AI generation function"""
import os
import sys

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'AssignEaseApi.settings')
import django
django.setup()

# Now test
from AssignEaseApp.llm import generate_database_assignment

print("\n" + "="*50)
print("Testing AI Database Assignment Generation")
print("="*50)

questions = [
    "Create a table for students with name and roll number",
    "Write a query to find students with roll number > 50"
]

print(f"\nInput questions:")
for i, q in enumerate(questions, 1):
    print(f"  {i}. {q}")

print(f"\nCalling generate_database_assignment()...")
print("(This may take 30-120 seconds, calling Ollama...)\n")

try:
    result = generate_database_assignment(questions)
    
    print("✓ SUCCESS! Got results from AI\n")
    
    print(f"Schema SQL ({len(result['schema_sql'])} chars):")
    print("-" * 40)
    print(result['schema_sql'][:200] + ("..." if len(result['schema_sql']) > 200 else ""))
    
    print(f"\nSample Data SQL ({len(result['sample_data_sql'])} chars):")
    print("-" * 40)
    print(result['sample_data_sql'][:200] + ("..." if len(result['sample_data_sql']) > 200 else ""))
    
    print(f"\nGenerated Questions: {len(result['questions'])}")
    print("-" * 40)
    for i, q in enumerate(result['questions'], 1):
        print(f"Q{i}: {q.get('question_text', 'N/A')[:60]}...")
        print(f"    Type: {q.get('question_type', 'N/A')}")
        print(f"    Query: {q.get('expected_query', 'N/A')[:50]}...")
    
    print("\n" + "="*50)
    print("✓ Test completed successfully!")
    print("="*50 + "\n")
    
except Exception as e:
    print(f"✗ ERROR: {type(e).__name__}")
    print(f"Message: {str(e)}")
    print("\nTraceback:")
    import traceback
    traceback.print_exc()
    print("\n" + "="*50 + "\n")
    sys.exit(1)
