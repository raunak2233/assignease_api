# Database Assignment API Endpoints Reference

## Base URL
```
http://localhost:8000/api/
```

## Authentication
All endpoints require JWT authentication:
```
Authorization: Bearer <access_token>
```

---

## 📚 Endpoints

### 1. Database Schemas

#### List/Create Schemas
```http
GET  /api/databaseschemas/
POST /api/databaseschemas/
```

**POST Request Body:**
```json
{
  "assignment": 1,
  "db_type": "sqlite",
  "schema_sql": "CREATE TABLE students (id INTEGER PRIMARY KEY, name TEXT NOT NULL, age INTEGER, grade TEXT);",
  "sample_data_sql": "INSERT INTO students VALUES (1, 'Alice', 20, 'A'); INSERT INTO students VALUES (2, 'Bob', 22, 'B');"
}
```

**Response:**
```json
{
  "id": 1,
  "assignment": 1,
  "assignment_title": "SQL Basics Assignment",
  "db_type": "sqlite",
  "schema_sql": "CREATE TABLE students...",
  "sample_data_sql": "INSERT INTO students...",
  "created_at": "2026-03-06T10:00:00Z",
  "updated_at": "2026-03-06T10:00:00Z"
}
```

#### Get/Update/Delete Schema
```http
GET    /api/databaseschemas/{id}/
PUT    /api/databaseschemas/{id}/
PATCH  /api/databaseschemas/{id}/
DELETE /api/databaseschemas/{id}/
```

---

### 2. Database Questions

#### List/Create Questions
```http
GET  /api/databasequestions/
POST /api/databasequestions/
```

**POST Request Body:**
```json
{
  "assignment": 1,
  "question_text": "Write a query to select all students with grade 'A', ordered by name",
  "expected_query": "SELECT * FROM students WHERE grade = 'A' ORDER BY name",
  "expected_result": [
    {"id": 1, "name": "Alice", "age": 20, "grade": "A"},
    {"id": 3, "name": "Charlie", "age": 21, "grade": "A"}
  ],
  "total_marks": 10.0,
  "order": 1,
  "hints": "Use WHERE clause to filter and ORDER BY to sort"
}
```

**Response:**
```json
{
  "id": 1,
  "assignment": 1,
  "assignment_title": "SQL Basics Assignment",
  "question_text": "Write a query to select all students with grade 'A'...",
  "expected_query": "SELECT * FROM students WHERE grade = 'A' ORDER BY name",
  "expected_result": [...],
  "total_marks": 10.0,
  "order": 1,
  "hints": "Use WHERE clause...",
  "created_at": "2026-03-06T10:00:00Z",
  "updated_at": "2026-03-06T10:00:00Z"
}
```

#### Get/Update/Delete Question
```http
GET    /api/databasequestions/{id}/
PUT    /api/databasequestions/{id}/
PATCH  /api/databasequestions/{id}/
DELETE /api/databasequestions/{id}/
```

---

### 3. Test Query (Practice Mode)

**Test query without submitting - for students to practice**

```http
POST /api/test-database-query/
```

**Request Body:**
```json
{
  "assignment_id": 1,
  "query": "SELECT name, grade FROM students WHERE grade = 'A'"
}
```

**Success Response:**
```json
{
  "success": true,
  "result": [
    {"name": "Alice", "grade": "A"},
    {"name": "Charlie", "grade": "A"}
  ],
  "execution_time": 0.52,
  "row_count": 2
}
```

**Error Response:**
```json
{
  "success": false,
  "error": "SQL Error: no such column: grades"
}
```

---

### 4. Database Submissions

#### List Submissions
```http
GET /api/databasesubmissions/
```

**Response:**
```json
[
  {
    "id": 1,
    "student": 5,
    "student_name": "john_doe",
    "student_email": "john@example.com",
    "assignment": 1,
    "assignment_title": "SQL Basics Assignment",
    "question": 1,
    "question_text": "Write a query to select all students...",
    "total_marks": 10.0,
    "submitted_query": "SELECT * FROM students WHERE grade = 'A' ORDER BY name",
    "query_result": [...],
    "is_correct": true,
    "execution_time": 0.45,
    "error_message": null,
    "auto_marks": 10.0,
    "custom_marks": null,
    "final_marks": 10.0,
    "status": "submitted",
    "feedback": "Results match perfectly! Well done!",
    "submitted_at": "2026-03-06T11:30:00Z",
    "updated_at": "2026-03-06T11:30:00Z"
  }
]
```

#### Submit Query
```http
POST /api/databasesubmissions/
```

**Request Body:**
```json
{
  "assignment": 1,
  "question": 1,
  "submitted_query": "SELECT * FROM students WHERE grade = 'A' ORDER BY name"
}
```

**Success Response (Correct Query):**
```json
{
  "id": 1,
  "student": 5,
  "student_name": "john_doe",
  "assignment": 1,
  "question": 1,
  "submitted_query": "SELECT * FROM students WHERE grade = 'A' ORDER BY name",
  "query_result": [
    {"id": 1, "name": "Alice", "age": 20, "grade": "A"},
    {"id": 3, "name": "Charlie", "age": 21, "grade": "A"}
  ],
  "is_correct": true,
  "execution_time": 0.45,
  "error_message": null,
  "auto_marks": 10.0,
  "custom_marks": null,
  "final_marks": 10.0,
  "status": "submitted",
  "feedback": "Results match perfectly! Well done!",
  "submitted_at": "2026-03-06T11:30:00Z"
}
```

**Response (Incorrect Query):**
```json
{
  "id": 2,
  "is_correct": false,
  "execution_time": 0.32,
  "auto_marks": 0.0,
  "feedback": "Row count mismatch: expected 2 rows, got 1 rows"
}
```

**Response (Query Error):**
```json
{
  "id": 3,
  "is_correct": false,
  "execution_time": null,
  "error_message": "SQL Error: no such column: grades",
  "auto_marks": 0.0,
  "feedback": "Error: SQL Error: no such column: grades"
}
```

#### Get Submission
```http
GET /api/databasesubmissions/{id}/
```

#### Update Submission (Teacher Only)
```http
PATCH /api/databasesubmissions/{id}/
```

**Request Body (Teacher Override):**
```json
{
  "custom_marks": 8.5,
  "status": "checked",
  "feedback": "Good attempt, but query could be optimized"
}
```

#### Get Student Submissions for Assignment
```http
GET /api/database-submissions/student/{student_id}/assignment/{assignment_id}/
```

**Response:**
```json
[
  {
    "id": 1,
    "question": 1,
    "question_text": "Select all students with grade A",
    "submitted_query": "SELECT * FROM students WHERE grade = 'A'",
    "is_correct": true,
    "auto_marks": 10.0,
    "final_marks": 10.0
  },
  {
    "id": 2,
    "question": 2,
    "question_text": "Count students by grade",
    "submitted_query": "SELECT grade, COUNT(*) FROM students GROUP BY grade",
    "is_correct": true,
    "auto_marks": 15.0,
    "final_marks": 15.0
  }
]
```

---

## 🔐 Access Control

### Teachers Can:
- Create/edit/delete database schemas
- Create/edit/delete database questions
- View all student submissions
- Override auto-marks with custom marks
- Update submission status
- Add custom feedback

### Students Can:
- View database schemas for their assignments
- View database questions for their assignments
- Test queries unlimited times (practice mode)
- Submit queries for grading
- View their own submissions
- See immediate feedback on correctness

---

## 🚨 Error Responses

### 400 Bad Request
```json
{
  "error": "Query cannot be empty"
}
```

### 404 Not Found
```json
{
  "error": "Assignment not found"
}
```

### 401 Unauthorized
```json
{
  "detail": "Authentication credentials were not provided."
}
```

---

## 💡 Usage Examples

### Example 1: Teacher Creates Database Assignment

```bash
# 1. Create assignment
curl -X POST http://localhost:8000/api/assignments/ \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "class_assigned": 1,
    "title": "SQL Basics",
    "description": "Learn SQL fundamentals",
    "due_date": "2026-04-01",
    "assignment_type": "database"
  }'

# 2. Create schema
curl -X POST http://localhost:8000/api/databaseschemas/ \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "assignment": 1,
    "db_type": "sqlite",
    "schema_sql": "CREATE TABLE students (id INTEGER PRIMARY KEY, name TEXT, grade TEXT);",
    "sample_data_sql": "INSERT INTO students VALUES (1, '\''Alice'\'', '\''A'\''); INSERT INTO students VALUES (2, '\''Bob'\'', '\''B'\'');"
  }'

# 3. Create question
curl -X POST http://localhost:8000/api/databasequestions/ \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "assignment": 1,
    "question_text": "Select all A-grade students",
    "expected_result": [{"id": 1, "name": "Alice", "grade": "A"}],
    "total_marks": 10
  }'
```

### Example 2: Student Tests and Submits

```bash
# 1. Test query (practice)
curl -X POST http://localhost:8000/api/test-database-query/ \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "assignment_id": 1,
    "query": "SELECT * FROM students WHERE grade = '\''A'\''"
  }'

# 2. Submit query
curl -X POST http://localhost:8000/api/databasesubmissions/ \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "assignment": 1,
    "question": 1,
    "submitted_query": "SELECT * FROM students WHERE grade = '\''A'\''"
  }'
```

---

## 📝 Notes

- All timestamps are in ISO 8601 format (UTC)
- Query results are stored as JSON arrays
- Execution time is in milliseconds
- Marks are floating-point numbers
- Status values: 'submitted', 'checked', 'reassigned', 'rejected'
- Database types: 'sqlite', 'mysql', 'postgresql' (only SQLite currently supported)

---

## ✅ Ready to Use

All endpoints are implemented and tested. You can start integrating with the frontend!
