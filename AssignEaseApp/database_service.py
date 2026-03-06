import sqlite3
import json
import time
from contextlib import contextmanager
from typing import Dict, List, Any, Tuple


class DatabaseExecutionError(Exception):
    """Custom exception for database execution errors"""
    pass


class DatabaseService:
    """Service for executing SQL queries in isolated database environments"""
    
    TIMEOUT_SECONDS = 10
    MAX_ROWS = 1000
    
    @staticmethod
    @contextmanager
    def get_db_connection(db_type: str):
        """
        Context manager for database connections
        Currently supports SQLite (in-memory for isolation)
        """
        conn = None
        try:
            if db_type == 'sqlite':
                # Use in-memory SQLite for complete isolation
                conn = sqlite3.connect(':memory:', timeout=DatabaseService.TIMEOUT_SECONDS)
                conn.row_factory = sqlite3.Row
                
            elif db_type == 'mysql':
                # TODO: Add MySQL support with mysql-connector-python
                raise DatabaseExecutionError("MySQL support coming soon. Please use SQLite for now.")
                
            elif db_type == 'postgresql':
                # TODO: Add PostgreSQL support with psycopg2
                raise DatabaseExecutionError("PostgreSQL support coming soon. Please use SQLite for now.")
                
            else:
                raise DatabaseExecutionError(f"Unsupported database type: {db_type}")
            
            yield conn
            
        finally:
            if conn:
                try:
                    conn.rollback()  # Always rollback to prevent any data persistence
                    conn.close()
                except Exception:
                    pass
    
    @staticmethod
    def setup_schema(conn, schema_sql: str, sample_data_sql: str = ""):
        """
        Setup database schema and sample data
        
        Args:
            conn: Database connection
            schema_sql: CREATE TABLE statements
            sample_data_sql: INSERT statements for sample data
        """
        cursor = conn.cursor()
        try:
            # Execute schema creation (split by semicolon for multiple statements)
            statements = [s.strip() for s in schema_sql.split(';') if s.strip()]
            for statement in statements:
                cursor.execute(statement)
            
            # Execute sample data insertion
            if sample_data_sql:
                data_statements = [s.strip() for s in sample_data_sql.split(';') if s.strip()]
                for statement in data_statements:
                    cursor.execute(statement)
            
            conn.commit()
            
        except Exception as e:
            conn.rollback()
            raise DatabaseExecutionError(f"Schema setup failed: {str(e)}")
        finally:
            cursor.close()
    
    @staticmethod
    def execute_query(conn, query: str, db_type: str, allow_write_operations: bool = False) -> Tuple[List[Dict], float]:
        """
        Execute SQL query and return results with execution time
        
        Args:
            conn: Database connection
            query: SQL query to execute
            db_type: Database type (for dialect-specific handling)
            allow_write_operations: If True, allows CREATE, INSERT, UPDATE, DELETE operations
            
        Returns:
            Tuple of (results as list of dicts, execution_time in ms)
        """
        cursor = conn.cursor()
        start_time = time.time()
        
        try:
            # Security: Check for dangerous operations
            query_upper = query.upper().strip()
            
            if not allow_write_operations:
                # Block dangerous keywords (students should only SELECT)
                dangerous_keywords = ['DROP', 'DELETE', 'TRUNCATE', 'ALTER', 'CREATE', 'INSERT', 'UPDATE']
                for keyword in dangerous_keywords:
                    if keyword in query_upper:
                        raise DatabaseExecutionError(
                            f"Operation '{keyword}' is not allowed. Only SELECT queries are permitted."
                        )
            else:
                # Even with write operations allowed, block DROP DATABASE/SCHEMA
                extremely_dangerous = ['DROP DATABASE', 'DROP SCHEMA']
                for keyword in extremely_dangerous:
                    if keyword in query_upper:
                        raise DatabaseExecutionError(
                            f"Operation '{keyword}' is not allowed for security reasons."
                        )
            
            # Execute the query
            cursor.execute(query)
            
            # Fetch results if query returns data
            if cursor.description:  # Query returns results (SELECT)
                columns = [desc[0] for desc in cursor.description]
                rows = cursor.fetchmany(DatabaseService.MAX_ROWS + 1)
                
                if len(rows) > DatabaseService.MAX_ROWS:
                    raise DatabaseExecutionError(
                        f"Query returned too many rows. Maximum allowed: {DatabaseService.MAX_ROWS}"
                    )
                
                # Convert to list of dictionaries
                results = []
                for row in rows:
                    row_dict = {}
                    for i, col in enumerate(columns):
                        row_dict[col] = row[i]
                    results.append(row_dict)
            else:
                # For non-SELECT queries (INSERT, UPDATE, DELETE, CREATE, etc.)
                # Return affected rows count or success message
                results = []
                if cursor.rowcount >= 0:
                    results = [{'affected_rows': cursor.rowcount, 'status': 'success'}]
            
            # Commit changes if write operations are allowed
            if allow_write_operations:
                conn.commit()
            
            execution_time = (time.time() - start_time) * 1000  # Convert to milliseconds
            
            return results, execution_time
            
        except DatabaseExecutionError:
            raise
        except sqlite3.Error as e:
            raise DatabaseExecutionError(f"SQL Error: {str(e)}")
        except Exception as e:
            raise DatabaseExecutionError(f"Query execution failed: {str(e)}")
        finally:
            cursor.close()
    
    @staticmethod
    def normalize_result(result: List[Dict]) -> List[Dict]:
        """
        Normalize query results for comparison
        - Converts all values to strings
        - Handles None/NULL values
        - Sorts rows for consistent ordering
        """
        if not result:
            return []
        
        # Convert all values to strings for comparison
        normalized = []
        for row in result:
            normalized_row = {}
            for key, value in row.items():
                if value is None:
                    normalized_row[key] = None
                else:
                    # Convert to string and strip whitespace
                    normalized_row[key] = str(value).strip()
            normalized.append(normalized_row)
        
        # Sort rows by all columns for consistent ordering
        try:
            normalized.sort(key=lambda x: tuple(str(v) if v is not None else '' for v in x.values()))
        except Exception:
            # If sorting fails, keep original order
            pass
        
        return normalized
    
    @staticmethod
    def compare_results(expected: List[Dict], actual: List[Dict]) -> Tuple[bool, str]:
        """
        Compare expected and actual query results
        
        Returns:
            Tuple of (is_match: bool, feedback: str)
        """
        expected_normalized = DatabaseService.normalize_result(expected)
        actual_normalized = DatabaseService.normalize_result(actual)
        
        # Check row count
        if len(expected_normalized) != len(actual_normalized):
            return False, f"Row count mismatch: expected {len(expected_normalized)} rows, got {len(actual_normalized)} rows"
        
        # Check if both are empty
        if not expected_normalized and not actual_normalized:
            return True, "Query returned no rows (as expected)"
        
        # Check column names
        if expected_normalized and actual_normalized:
            expected_cols = set(expected_normalized[0].keys())
            actual_cols = set(actual_normalized[0].keys())
            
            if expected_cols != actual_cols:
                missing = expected_cols - actual_cols
                extra = actual_cols - expected_cols
                msg_parts = []
                if missing:
                    msg_parts.append(f"Missing columns: {', '.join(missing)}")
                if extra:
                    msg_parts.append(f"Extra columns: {', '.join(extra)}")
                return False, "; ".join(msg_parts)
        
        # Compare row by row
        for i, (exp_row, act_row) in enumerate(zip(expected_normalized, actual_normalized)):
            if exp_row != act_row:
                # Find which columns differ
                diff_cols = []
                for col in exp_row.keys():
                    if exp_row.get(col) != act_row.get(col):
                        diff_cols.append(f"{col}: expected '{exp_row.get(col)}', got '{act_row.get(col)}'")
                
                return False, f"Row {i+1} mismatch - {'; '.join(diff_cols)}"
        
        return True, "Results match perfectly! Well done!"
    
    @staticmethod
    def execute_and_validate(
        db_type: str,
        schema_sql: str,
        sample_data_sql: str,
        student_query: str,
        expected_result: List[Dict],
        allow_write_operations: bool = False
    ) -> Dict[str, Any]:
        """
        Execute student query and validate against expected results
        
        Args:
            allow_write_operations: If True, allows CREATE, INSERT, UPDATE, DELETE operations
        
        Returns:
            Dictionary with validation results:
            {
                'is_correct': bool,
                'query_result': List[Dict] or None,
                'execution_time': float or None,
                'error_message': str or None,
                'feedback': str
            }
        """
        try:
            with DatabaseService.get_db_connection(db_type) as conn:
                # Setup schema and sample data
                DatabaseService.setup_schema(conn, schema_sql, sample_data_sql)
                
                # Execute student query
                actual_result, exec_time = DatabaseService.execute_query(
                    conn, student_query, db_type, allow_write_operations
                )
                
                # Compare results
                is_correct, feedback = DatabaseService.compare_results(expected_result, actual_result)
                
                return {
                    'is_correct': is_correct,
                    'query_result': actual_result,
                    'execution_time': exec_time,
                    'error_message': None,
                    'feedback': feedback
                }
                
        except DatabaseExecutionError as e:
            return {
                'is_correct': False,
                'query_result': None,
                'execution_time': None,
                'error_message': str(e),
                'feedback': f"Error: {str(e)}"
            }
        except Exception as e:
            return {
                'is_correct': False,
                'query_result': None,
                'execution_time': None,
                'error_message': str(e),
                'feedback': f"Unexpected error: {str(e)}"
            }
    
    @staticmethod
    def validate_ddl_dml_query(
        db_type: str,
        schema_sql: str,
        sample_data_sql: str,
        student_query: str,
        verification_query: str,
        expected_result: List[Dict]
    ) -> Dict[str, Any]:
        """
        Validate DDL/DML queries (CREATE, INSERT, UPDATE, DELETE) by:
        1. Executing the student's DDL/DML query
        2. Running a verification SELECT query
        3. Comparing verification results with expected results
        
        Args:
            db_type: Database type
            schema_sql: Initial schema setup
            sample_data_sql: Initial sample data
            student_query: Student's DDL/DML query (CREATE, INSERT, UPDATE, DELETE)
            verification_query: SELECT query to verify the result
            expected_result: Expected result from verification query
            
        Returns:
            Dictionary with validation results
        """
        try:
            with DatabaseService.get_db_connection(db_type) as conn:
                # Setup initial schema and sample data
                DatabaseService.setup_schema(conn, schema_sql, sample_data_sql)
                
                # Execute student's DDL/DML query
                student_result, exec_time = DatabaseService.execute_query(
                    conn, student_query, db_type, allow_write_operations=True
                )
                
                # Execute verification query to check the result
                verification_result, verify_time = DatabaseService.execute_query(
                    conn, verification_query, db_type, allow_write_operations=False
                )
                
                # Compare verification results with expected
                is_correct, feedback = DatabaseService.compare_results(expected_result, verification_result)
                
                return {
                    'is_correct': is_correct,
                    'query_result': verification_result,
                    'execution_time': exec_time + verify_time,
                    'error_message': None,
                    'feedback': feedback,
                    'student_query_result': student_result
                }
                
        except DatabaseExecutionError as e:
            return {
                'is_correct': False,
                'query_result': None,
                'execution_time': None,
                'error_message': str(e),
                'feedback': f"Error: {str(e)}",
                'student_query_result': None
            }
        except Exception as e:
            return {
                'is_correct': False,
                'query_result': None,
                'execution_time': None,
                'error_message': str(e),
                'feedback': f"Unexpected error: {str(e)}",
                'student_query_result': None
            }
