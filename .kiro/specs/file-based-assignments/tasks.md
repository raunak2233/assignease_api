# Implementation Plan

- [-] 1. Extend Assignment model for file-based assignments



  - Add new fields: assignment_type, submission_type, allowed_file_formats, max_file_size_mb, max_files_per_submission
  - Update existing Assignment model with new choices and defaults
  - Create and run Django migration for Assignment model changes
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 2.1, 2.2, 2.3, 2.4, 2.5_

- [ ] 2. Create AssignmentAttachment model



  - Define AssignmentAttachment model with file field and metadata
  - Set up proper file upload path and naming strategy
  - Create foreign key relationship to Assignment model
  - Create and run Django migration for new AssignmentAttachment model
  - _Requirements: 6.1, 6.2, 6.3_

- [ ] 3. Enhance Submission model for mixed content




  - Rename 'code' field to 'text_content' for clarity
  - Add submission_type field to track content type (text/files/mixed)
  - Update model constraints and validation
  - Create and run Django migration for Submission model changes
  - _Requirements: 3.5, 4.1, 4.4_

- [ ] 4. Create SubmissionFile model



  - Define SubmissionFile model with file field and metadata tracking
  - Set up secure file upload path with student/assignment organization
  - Create foreign key relationship to Submission model
  - Add file type and size tracking fields
  - Create and run Django migration for new SubmissionFile model
  - _Requirements: 3.4, 4.1, 4.2, 5.2_

- [ ] 5. Update Assignment serializer for file support



  - Add new fields to AssignmentSerializer (assignment_type, submission_type, etc.)
  - Create nested AssignmentAttachmentSerializer for file attachments
  - Implement file format validation in serializer
  - Add file size and count validation logic
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 2.1, 6.1, 6.2_

- [ ] 6. Create SubmissionFile serializer and update Submission serializer



  - Create SubmissionFileSerializer for file upload handling
  - Update SubmissionSerializer to handle both text and file content
  - Implement multipart form data handling for file uploads
  - Add validation for submission type compatibility
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6_

- [ ] 7. Implement file validation utilities



  - Create file format validation function using python-magic
  - Implement file size validation with configurable limits
  - Add filename sanitization to prevent security issues
  - Create file count validation for submissions
  - _Requirements: 3.2, 3.3, 3.6, 5.1, 5.2, 5.3_

- [ ] 8. Update Assignment views for file-based assignments



  - Modify AssignmentViewSet to handle file attachments
  - Add endpoint for uploading assignment attachments
  - Update assignment creation to validate file configuration
  - Add endpoint for downloading assignment attachments
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 6.1, 6.2, 6.3, 6.4_

- [ ] 9. Update Submission views for file uploads



  - Modify SubmissionViewSet to handle multipart form data
  - Add file upload validation in submission creation
  - Implement secure file download endpoint with permission checks
  - Add endpoint for deleting submission files before final submission
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 4.2, 5.3_
-

- [ ] 10. Add URL patterns for new file endpoints


  - Add URL patterns for assignment attachment upload/download
  - Add URL patterns for submission file upload/download/delete
  - Update existing URL patterns to support new functionality
  - Ensure proper URL naming for reverse lookups
  - _Requirements: 4.2, 6.3_

- [ ] 11. Implement file security and permissions



  - Add permission checks for file access (students can only access their files)
  - Implement secure file serving using Django's FileResponse
  - Add file access logging for audit trails
  - Implement rate limiting for file uploads
  - _Requirements: 5.2, 5.3, 4.2_

- [ ] 12. Update error handling for file operations



  - Add specific error handling for file upload failures
  - Implement proper error messages for validation failures
  - Add error handling for file download issues
  - Create consistent error response format for file operations
  - _Requirements: 3.6, 5.5_

- [ ]* 13. Write unit tests for new models and serializers
  - Test Assignment model with new file-related fields
  - Test AssignmentAttachment and SubmissionFile model creation
  - Test serializer validation for file uploads and formats
  - Test file validation utility functions
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 3.2, 3.3, 3.6_

- [ ]* 14. Write integration tests for file upload workflows
  - Test complete assignment creation with file attachments
  - Test student submission with mixed text and file content
  - Test file download and access permission workflows
  - Test error scenarios for invalid files and permissions
  - _Requirements: 3.1, 3.4, 3.5, 4.1, 4.2, 5.3_

- [ ] 15. Configure Django settings for file handling



  - Update MEDIA_ROOT and MEDIA_URL settings for file storage
  - Configure file upload size limits in Django settings
  - Add file type validation settings
  - Set up proper static file serving for development
  - _Requirements: 1.3, 1.4, 5.2, 5.4_
-

- [ ] 16. Update existing views to handle backward compatibility


  - Ensure existing coding assignments continue to work
  - Update assignment list views to show assignment type
  - Modify submission views to handle both old and new submission formats
  - Add migration path for existing data
  - _Requirements: 2.1, 2.2, 2.3, 4.4_