# Generated migration file

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('AssignEaseApp', '0002_alter_assignment_assignment_type_databasequestion_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='databasequestion',
            name='question_type',
            field=models.CharField(
                choices=[('select', 'SELECT Query (Read-only)'), ('ddl_dml', 'DDL/DML Query (CREATE, INSERT, UPDATE, DELETE)')],
                default='select',
                max_length=20
            ),
        ),
        migrations.AddField(
            model_name='databasequestion',
            name='verification_query',
            field=models.TextField(
                blank=True,
                help_text='SELECT query to verify DDL/DML results (only for ddl_dml type)',
                null=True
            ),
        ),
    ]
