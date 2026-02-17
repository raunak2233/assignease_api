# Requirements Document

## Introduction

This feature extends the existing AssignEase application to support non-coding assignments that allow file uploads and flexible submission types. Teachers will be able to create assignments that accept various file formats (images, documents, spreadsheets) and configure whether students can submit text, files, or both. This mirrors the functionality found in Google Classroom, providing a comprehensive assignment management system for both coding and non-coding coursework.

## Requirements

### Requirement 1

**User Story:** As a teacher, I want to create non-coding assignments that accept file uploads, so that I can assign projects, essays, presentations, and other non-programming tasks to my students.

#### Acceptance Criteria

1. WHEN a teacher creates a new assignment THEN the system SHALL provide an option to select assignment type (coding or non-coding)
2. WHEN creating a non-coding assignment THEN the system SHALL allow the teacher to specify accepted file formats (jpg, png, pdf, docx, xlsx, csv, pptx, etc.)
3. WHEN creating a non-coding assignment THEN the system SHALL allow the teacher to set file size limits
4. WHEN creating a non-coding assignment THEN the system SHALL allow the teacher to specify maximum number of files per submission

### Requirement 2

**User Story:** As a teacher, I want to configure submission types for assignments, so that I can control whether students submit text, files, or both based on the assignment requirements.

#### Acceptance Criteria

1. WHEN creating an assignment THEN the teacher SHALL be able to choose from submission types: "text_only", "files_only", or "text_and_files"
2. WHEN submission type is "text_only" THEN the system SHALL only allow text submissions from students
3. WHEN submission type is "files_only" THEN the system SHALL only allow file uploads from students
4. WHEN submission type is "text_and_files" THEN the system SHALL allow both text and file submissions from students
5. IF submission type is "files_only" or "text_and_files" THEN the system SHALL validate uploaded files against allowed formats

### Requirement 3

**User Story:** As a student, I want to submit assignments with files and/or text, so that I can complete various types of coursework including essays, presentations, and project deliverables.

#### Acceptance Criteria

1. WHEN a student views an assignment THEN the system SHALL display the allowed submission types and file formats
2. WHEN submitting a file-based assignment THEN the system SHALL validate file format against allowed types
3. WHEN submitting a file-based assignment THEN the system SHALL validate file size against limits
4. WHEN submitting files THEN the system SHALL store files securely with unique identifiers
5. WHEN submitting text and files THEN the system SHALL save both components as part of the same submission
6. WHEN a file upload fails validation THEN the system SHALL display clear error messages to the student

### Requirement 4

**User Story:** As a teacher, I want to view and manage file submissions from students, so that I can review, grade, and provide feedback on submitted work.

#### Acceptance Criteria

1. WHEN viewing student submissions THEN the teacher SHALL see both text content and uploaded files
2. WHEN viewing file submissions THEN the teacher SHALL be able to download individual files
3. WHEN providing feedback THEN the teacher SHALL be able to comment on both text and file submissions
4. WHEN grading submissions THEN the system SHALL support the same status workflow (submitted, checked, reassigned, rejected)

### Requirement 5

**User Story:** As a system administrator, I want file uploads to be secure and manageable, so that the system remains stable and protected from malicious uploads.

#### Acceptance Criteria

1. WHEN files are uploaded THEN the system SHALL scan for malicious content
2. WHEN files are stored THEN the system SHALL use secure file naming to prevent conflicts
3. WHEN files are accessed THEN the system SHALL verify user permissions
4. WHEN storage limits are reached THEN the system SHALL prevent new uploads and notify administrators
5. IF a file is corrupted or inaccessible THEN the system SHALL handle errors gracefully

### Requirement 6

**User Story:** As a teacher, I want to set assignment instructions and attachments, so that I can provide clear guidance and reference materials for student submissions.

#### Acceptance Criteria

1. WHEN creating an assignment THEN the teacher SHALL be able to attach reference files
2. WHEN creating an assignment THEN the teacher SHALL be able to provide detailed instructions
3. WHEN students view assignments THEN they SHALL see all instruction text and downloadable attachments
4. WHEN assignment attachments are updated THEN students SHALL be notified of changes