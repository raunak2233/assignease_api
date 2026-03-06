"""
Standalone test for database service (no Django required)
This tests the core database execution logic
"""

import sys
import os

# Add the app directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'AssignEaseApp'))

from database_service import DatabaseService

def test_basic_query():
    """Test basic SELECT query"""
    print("=" * 70)
    print("TEST 1: Basic SELECT Query")
    print("=" * 70)
    
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
    INSERT INTO students (id, name, age, grade) VALUES (4, 'Diana', 23, 'B');
    """
    
    student_query = "SELECT name, grade FROM students WHERE grade = 'A' ORDER BY name"
    
    expected_result = [
        {'name': 'Alice', 'grade': 'A'},
        {'name': 'Charlie', 'grade': 'A'}
    ]
    
    result = DatabaseService.execute_and_validate(
        db_type='sqlite',
        schema_sql=schema_sql,
        sample_data_sql=sample_data_sql,
        student_query=student_query,
        expected_result=expected_result
    )
    
    print(f"\n✓ Query: {student_query}")
    print(f"✓ Is Correct: {result['is_correct']}")
    print(f"✓ Execution Time: {result['execution_time']:.2f}ms")
    print(f"✓ Feedback: {result['feedback']}")
    print(f"✓ Result: {result['query_result']}")
    
    assert result['is_correct'] == True, "Query should be correct"
    print("\n✅ TEST PASSED\n")


def test_incorrect_query():
    """Test query with wrong results"""
    print("=" * 70)
    print("TEST 2: Incorrect Query (Wrong Columns)")
    print("=" * 70)
    
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
    """
    
    # Student query returns only name, but expected has name and grade
    student_query = "SELECT name FROM students WHERE grade = 'A'"
    
    expected_result = [
        {'name': 'Alice', 'grade': 'A'}
    ]
    
    result = DatabaseService.execute_and_validate(
        db_type='sqlite',
        schema_sql=schema_sql,
        sample_data_sql=sample_data_sql,
        student_query=student_query,
        expected_result=expected_result
    )
    
    print(f"\n✓ Query: {student_query}")
    print(f"✓ Is Correct: {result['is_correct']}")
    print(f"✓ Feedback: {result['feedback']}")
    
    assert result['is_correct'] == False, "Query should be incorrect"
    print("\n✅ TEST PASSED\n")


def test_dangerous_query():
    """Test that dangerous queries are blocked"""
    print("=" * 70)
    print("TEST 3: Dangerous Query (Should be Blocked)")
    print("=" * 70)
    
    schema_sql = "CREATE TABLE test (id INTEGER);"
    sample_data_sql = "INSERT INTO test VALUES (1);"
    
    dangerous_queries = [
        "DROP TABLE test",
        "DELETE FROM test",
        "INSERT INTO test VALUES (2)",
        "UPDATE test SET id = 5",
        "ALTER TABLE test ADD COLUMN name TEXT"
    ]
    
    for query in dangerous_queries:
        result = DatabaseService.execute_and_validate(
            db_type='sqlite',
            schema_sql=schema_sql,
            sample_data_sql=sample_data_sql,
            student_query=query,
            expected_result=[]
        )
        
        print(f"\n✓ Query: {query}")
        print(f"✓ Blocked: {result['error_message'] is not None}")
        print(f"✓ Error: {result['error_message']}")
        
        assert result['error_message'] is not None, f"Query '{query}' should be blocked"
    
    print("\n✅ TEST PASSED\n")


def test_join_query():
    """Test JOIN query"""
    print("=" * 70)
    print("TEST 4: JOIN Query")
    print("=" * 70)
    
    schema_sql = """
    CREATE TABLE students (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL
    );
    
    CREATE TABLE grades (
        student_id INTEGER,
        subject TEXT,
        grade TEXT,
        FOREIGN KEY (student_id) REFERENCES students(id)
    );
    """
    
    sample_data_sql = """
    INSERT INTO students VALUES (1, 'Alice');
    INSERT INTO students VALUES (2, 'Bob');
    INSERT INTO grades VALUES (1, 'Math', 'A');
    INSERT INTO grades VALUES (1, 'Science', 'B');
    INSERT INTO grades VALUES (2, 'Math', 'B');
    """
    
    student_query = """
    SELECT s.name, g.subject, g.grade 
    FROM students s 
    JOIN grades g ON s.id = g.student_id 
    WHERE g.grade = 'A'
    ORDER BY s.name, g.subject
    """
    
    expected_result = [
        {'name': 'Alice', 'subject': 'Math', 'grade': 'A'}
    ]
    
    result = DatabaseService.execute_and_validate(
        db_type='sqlite',
        schema_sql=schema_sql,
        sample_data_sql=sample_data_sql,
        student_query=student_query,
        expected_result=expected_result
    )
    
    print(f"\n✓ Query: {student_query}")
    print(f"✓ Is Correct: {result['is_correct']}")
    print(f"✓ Execution Time: {result['execution_time']:.2f}ms")
    print(f"✓ Feedback: {result['feedback']}")
    
    assert result['is_correct'] == True, "JOIN query should be correct"
    print("\n✅ TEST PASSED\n")


def test_aggregate_query():
    """Test aggregate functions"""
    print("=" * 70)
    print("TEST 5: Aggregate Query (COUNT, AVG)")
    print("=" * 70)
    
    schema_sql = """
    CREATE TABLE sales (
        id INTEGER PRIMARY KEY,
        product TEXT,
        amount REAL
    );
    """
    
    sample_data_sql = """
    INSERT INTO sales VALUES (1, 'Laptop', 1000.00);
    INSERT INTO sales VALUES (2, 'Mouse', 25.50);
    INSERT INTO sales VALUES (3, 'Keyboard', 75.00);
    INSERT INTO sales VALUES (4, 'Monitor', 300.00);
    """
    
    student_query = "SELECT COUNT(*) as total_items, SUM(amount) as total_sales FROM sales"
    
    expected_result = [
        {'total_items': 4, 'total_sales': 1400.50}
    ]
    
    result = DatabaseService.execute_and_validate(
        db_type='sqlite',
        schema_sql=schema_sql,
        sample_data_sql=sample_data_sql,
        student_query=student_query,
        expected_result=expected_result
    )
    
    print(f"\n✓ Query: {student_query}")
    print(f"✓ Is Correct: {result['is_correct']}")
    print(f"✓ Result: {result['query_result']}")
    
    assert result['is_correct'] == True, "Aggregate query should be correct"
    print("\n✅ TEST PASSED\n")


if __name__ == '__main__':
    print("\n" + "🚀 " * 20)
    print("DATABASE SERVICE STANDALONE TESTS")
    print("🚀 " * 20 + "\n")
    
    try:
        test_basic_query()
        test_incorrect_query()
        test_dangerous_query()
        test_join_query()
        test_aggregate_query()
        
        print("\n" + "=" * 70)
        print("✅ ALL TESTS PASSED!")
        print("=" * 70)
        print("\nThe database service is working correctly!")
        print("You can now proceed with Django migrations and API testing.\n")
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}\n")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)
