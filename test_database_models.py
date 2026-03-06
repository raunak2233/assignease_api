"""
Test script to verify database assignment models and service
Run this after migrations: python test_database_models.py
"""

import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'AssignEaseApi.settings')
django.setup()

from AssignEaseApp.models import DatabaseSchema, DatabaseQuestion, DatabaseSubmission
from AssignEaseApp.database_service import DatabaseService

def test_database_service():
    """Test the database service with a simple query"""
    print("=" * 60)
    print("Testing Database Service")
    print("=" * 60)
    
    # Test schema
    schema_sql = """
    CREATE TABLE students (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        age INTEGER,
        grade TEXT
    );
    """
    
    sample_data_sql = """
    INSERT INTO students (id, name, age, grade) VALUES (1, 'Alice', 20, 'A');
    INSERT INTO students (id, name, age, grade) VALUES (2, 'Bob', 22, 'B');
    INSERT INTO students (id, name, age, grade) VALUES (3, 'Charlie', 21, 'A');
    """
    
    # Test query
    student_query = "SELECT name, grade FROM students WHERE grade = 'A' ORDER BY name"
    
    # Expected result
    expected_result = [
        {'name': 'Alice', 'grade': 'A'},
        {'name': 'Charlie', 'grade': 'A'}
    ]
    
    print("\n1. Testing query execution...")
    result = DatabaseService.execute_and_validate(
        db_type='sqlite',
        schema_sql=schema_sql,
        sample_data_sql=sample_data_sql,
        student_query=student_query,
        expected_result=expected_result
    )
    
    print(f"   Is Correct: {result['is_correct']}")
    print(f"   Execution Time: {result['execution_time']:.2f}ms")
    print(f"   Feedback: {result['feedback']}")
    print(f"   Query Result: {result['query_result']}")
    
    # Test incorrect query
    print("\n2. Testing incorrect query...")
    wrong_query = "SELECT name FROM students WHERE grade = 'B'"
    
    result2 = DatabaseService.execute_and_validate(
        db_type='sqlite',
        schema_sql=schema_sql,
        sample_data_sql=sample_data_sql,
        student_query=wrong_query,
        expected_result=expected_result
    )
    
    print(f"   Is Correct: {result2['is_correct']}")
    print(f"   Feedback: {result2['feedback']}")
    
    # Test dangerous query
    print("\n3. Testing dangerous query (should be blocked)...")
    dangerous_query = "DROP TABLE students"
    
    result3 = DatabaseService.execute_and_validate(
        db_type='sqlite',
        schema_sql=schema_sql,
        sample_data_sql=sample_data_sql,
        student_query=dangerous_query,
        expected_result=expected_result
    )
    
    print(f"   Is Correct: {result3['is_correct']}")
    print(f"   Error: {result3['error_message']}")
    
    print("\n" + "=" * 60)
    print("All tests completed!")
    print("=" * 60)

def check_models():
    """Check if models are properly registered"""
    print("\n" + "=" * 60)
    print("Checking Database Models")
    print("=" * 60)
    
    print(f"\n✓ DatabaseSchema model: {DatabaseSchema}")
    print(f"✓ DatabaseQuestion model: {DatabaseQuestion}")
    print(f"✓ DatabaseSubmission model: {DatabaseSubmission}")
    
    print("\nModels are properly registered!")

if __name__ == '__main__':
    try:
        check_models()
        test_database_service()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
