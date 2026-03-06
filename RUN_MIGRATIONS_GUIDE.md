# Database Assignment Migrations Guide

## Issue
When trying to create a database assignment, you get the error:
```
assignment_type: ["database" is not a valid choice."]
```

This happens because the database hasn't been updated with the new "database" assignment type.

## Solution

### Step 1: Navigate to the API directory
```bash
cd AssignEaseAPI/AssignEaseApi
```

### Step 2: Create migrations
```bash
python manage.py makemigrations AssignEaseApp
```

You should see output like:
```
Migrations for 'AssignEaseApp':
  AssignEaseApp/migrations/0002_auto_XXXXXX.py
    - Alter field assignment_type on assignment
    - Create model DatabaseSchema
    - Create model DatabaseQuestion
    - Create model DatabaseSubmission
```

### Step 3: Apply migrations
```bash
python manage.py migrate
```

You should see output like:
```
Running migrations:
  Applying AssignEaseApp.0002_auto_XXXXXX... OK
```

### Step 4: Verify the changes
```bash
python manage.py shell
```

Then in the Python shell:
```python
from AssignEaseApp.models import Assignment
print(Assignment.ASSIGNMENT_TYPE_CHOICES)
# Should show: [('coding', 'Coding'), ('non_coding', 'Non-Coding'), ('database', 'Database')]

from AssignEaseApp.models import DatabaseSchema, DatabaseQuestion, DatabaseSubmission
print("Models imported successfully!")
exit()
```

### Step 5: Restart your Django server
If the server is running, restart it:
```bash
# Stop the server (Ctrl+C)
# Then start it again
python manage.py runserver
```

## After Migrations

Once migrations are complete, you can:
1. Go to the teacher panel
2. Click "Create Assignment"
3. Select "Database Assignment (SQL)"
4. Fill in the details
5. Click "Next: Configure Database"
6. The database configuration wizard will open!

## Troubleshooting

### If you get "No changes detected"
This means migrations were already created. Just run:
```bash
python manage.py migrate
```

### If you get migration conflicts
```bash
python manage.py migrate --fake AssignEaseApp zero
python manage.py migrate AssignEaseApp
```

### If you need to reset migrations (CAUTION: This will delete data!)
```bash
# Delete all migration files except __init__.py
# Then:
python manage.py makemigrations AssignEaseApp
python manage.py migrate
```

## What Gets Created

The migrations will:
1. Add "database" to Assignment.ASSIGNMENT_TYPE_CHOICES
2. Create DatabaseSchema table
3. Create DatabaseQuestion table
4. Create DatabaseSubmission table
5. Set up all foreign key relationships

## Next Steps

After successful migration:
- Test creating a database assignment
- Define a schema with CREATE TABLE statements
- Add questions with expected SQL queries
- Test the complete workflow!
