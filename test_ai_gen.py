#!/usr/bin/env python
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'AssignEaseApi.settings')
import django
django.setup()

from AssignEaseApp.llm import generate_database_assignment

test_questions = ['Create a table with student names and scores', 'Write a query to find the top scorer']

print('[TEST] Starting AI generation test...')
try:
    result = generate_database_assignment(test_questions)
    print('[TEST] SUCCESS!')
    print(f'[TEST] Schema length: {len(result["schema_sql"])} chars')
    print(f'[TEST] Sample data length: {len(result["sample_data_sql"])} chars')
    print(f'[TEST] Questions generated: {len(result["questions"])}')
    for i, q in enumerate(result["questions"], 1):
        print(f'  Q{i}: {q.get("question_text", "N/A")[:50]}...')
except Exception as e:
    print(f'[TEST] ERROR: {type(e).__name__}: {str(e)}')
    import traceback
    traceback.print_exc()
