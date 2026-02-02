"""
Utility functions for validation, error handling, and common operations.
"""

from typing import Optional, List
from fastapi import HTTPException, UploadFile
import re


class ValidationError(Exception):
    """Custom validation error exception."""
    pass


class FileValidator:
    """Validates uploaded files."""

    # Allowed file extensions and their MIME types
    ALLOWED_EXTENSIONS = {
        '.pdf': 'application/pdf',
        '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        '.doc': 'application/msword',
        '.csv': 'text/csv',
        '.json': 'application/json',
        '.txt': 'text/plain'
    }

    # Maximum file size (50 MB)
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB in bytes

    @staticmethod
    def validate_file(file: UploadFile) -> None:
        """
        Validate uploaded file for type and size.

        Args:
            file: The uploaded file to validate

        Raises:
            ValidationError: If file is invalid
        """
        if not file or not file.filename:
            raise ValidationError("No file provided or filename is empty")

        # Check file extension
        file_ext = '.' + file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else ''

        if file_ext not in FileValidator.ALLOWED_EXTENSIONS:
            allowed = ', '.join(FileValidator.ALLOWED_EXTENSIONS.keys())
            raise ValidationError(
                f"Invalid file type '{file_ext}'. Allowed types: {allowed}"
            )

        # Check file size (if available)
        if hasattr(file, 'size') and file.size:
            if file.size > FileValidator.MAX_FILE_SIZE:
                max_mb = FileValidator.MAX_FILE_SIZE / (1024 * 1024)
                raise ValidationError(
                    f"File size exceeds maximum allowed size of {max_mb:.0f} MB"
                )

    @staticmethod
    def get_file_extension(filename: str) -> str:
        """Get the file extension from filename."""
        return '.' + filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''


class QueryValidator:
    """Validates query inputs."""

    # Minimum and maximum question length
    MIN_QUESTION_LENGTH = 3
    MAX_QUESTION_LENGTH = 1000

    # SQL keywords that might indicate dangerous operations
    DANGEROUS_SQL_PATTERNS = [
        r'\bDROP\s+TABLE\b',
        r'\bDELETE\s+FROM\b',
        r'\bTRUNCATE\b',
        r'\bALTER\s+TABLE\b',
        r'\bCREATE\s+TABLE\b',
        r'\bINSERT\s+INTO\b',
        r'\bUPDATE\s+\w+\s+SET\b'
    ]

    @staticmethod
    def validate_question(question: str, allow_empty: bool = False) -> str:
        """
        Validate a question string.

        Args:
            question: The question to validate
            allow_empty: Whether to allow empty questions

        Returns:
            Cleaned question string

        Raises:
            ValidationError: If question is invalid
        """
        if not question or not question.strip():
            if allow_empty:
                return ""
            raise ValidationError("Question cannot be empty")

        question = question.strip()

        # Check length
        if len(question) < QueryValidator.MIN_QUESTION_LENGTH:
            raise ValidationError(
                f"Question too short (minimum {QueryValidator.MIN_QUESTION_LENGTH} characters)"
            )

        if len(question) > QueryValidator.MAX_QUESTION_LENGTH:
            raise ValidationError(
                f"Question too long (maximum {QueryValidator.MAX_QUESTION_LENGTH} characters)"
            )

        return question

    @staticmethod
    def validate_top_k(top_k: int) -> int:
        """
        Validate top_k parameter for retrieval.

        Args:
            top_k: Number of chunks to retrieve

        Returns:
            Validated top_k value

        Raises:
            ValidationError: If top_k is invalid
        """
        if not isinstance(top_k, int):
            raise ValidationError("top_k must be an integer")

        if top_k < 1:
            raise ValidationError("top_k must be at least 1")

        if top_k > 10:
            raise ValidationError("top_k cannot exceed 10")

        return top_k

    @staticmethod
    def check_dangerous_sql(sql: str) -> bool:
        """
        Check if SQL contains potentially dangerous operations.

        Args:
            sql: SQL query to check

        Returns:
            True if dangerous patterns found, False otherwise
        """
        sql_upper = sql.upper()

        for pattern in QueryValidator.DANGEROUS_SQL_PATTERNS:
            if re.search(pattern, sql_upper, re.IGNORECASE):
                return True

        return False

    @staticmethod
    def sanitize_sql_for_display(sql: str) -> str:
        """
        Sanitize SQL for safe display (remove comments, normalize whitespace).

        Args:
            sql: SQL query to sanitize

        Returns:
            Sanitized SQL string
        """
        # Remove SQL comments
        sql = re.sub(r'--.*$', '', sql, flags=re.MULTILINE)
        sql = re.sub(r'/\*.*?\*/', '', sql, flags=re.DOTALL)

        # Normalize whitespace
        sql = ' '.join(sql.split())

        return sql.strip()


class ErrorResponse:
    """Structured error response generator."""

    @staticmethod
    def validation_error(message: str, field: Optional[str] = None) -> dict:
        """Generate validation error response."""
        response = {
            "error": "Validation Error",
            "message": message,
            "type": "validation_error"
        }
        if field:
            response["field"] = field
        return response

    @staticmethod
    def service_unavailable(service_name: str, reason: Optional[str] = None) -> dict:
        """Generate service unavailable error response."""
        message = f"{service_name} is not available"
        if reason:
            message += f": {reason}"

        return {
            "error": "Service Unavailable",
            "message": message,
            "service": service_name,
            "type": "service_unavailable"
        }

    @staticmethod
    def internal_error(operation: str, error: Exception) -> dict:
        """Generate internal error response."""
        return {
            "error": "Internal Error",
            "message": f"Failed to {operation}",
            "details": str(error),
            "type": "internal_error"
        }


def format_file_size(size_bytes: int) -> str:
    """
    Format file size in human-readable format.

    Args:
        size_bytes: File size in bytes

    Returns:
        Formatted string (e.g., "2.5 MB")
    """
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    Truncate text to maximum length.

    Args:
        text: Text to truncate
        max_length: Maximum length
        suffix: Suffix to add if truncated

    Returns:
        Truncated text
    """
    if len(text) <= max_length:
        return text

    return text[:max_length - len(suffix)] + suffix
