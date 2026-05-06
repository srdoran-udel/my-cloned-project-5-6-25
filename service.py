"""Service layer for student enrollment system.

This module contains the EnrollmentService class which handles all business logic,
validation, and orchestration. It coordinates between the database layer and the
application layer.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

import config
from database import SQLDatabase


class EnrollmentError(Exception):
    """Exception raised for enrollment business logic errors."""

    pass


class EnrollmentService:
    """Business logic and orchestration for student enrollment."""

    def __init__(
        self, database: SQLDatabase, current_user_id: Optional[str] = None
    ) -> None:
        """
        Initialize enrollment service with a database.

        Args:
            database: SQLDatabase instance for data access.
            current_user_id: Optional user ID for context (used in UI).
        """
        self.db = database
        self.current_user_id = current_user_id

    def enroll_student_with_key(
        self, user_id: str, email: str, enrollment_key: str
    ) -> dict[str, Any]:
        """
        Enroll a student using an enrollment key.

        Business logic:
            1. Validate inputs (user_id, email format, enrollment_key present)
            2. Lookup course by enrollment key
            3. Create or reactivate enrollment record
            4. Return the enrollment record

        Args:
            user_id: Student's user ID.
            email: Student's email address.
            enrollment_key: The course enrollment key to use.

        Returns:
            Enrollment record dict with keys: enrollment_id, user_id, email,
            course_id, status, enrolled_at

        Raises:
            EnrollmentError: If validation fails or enrollment_key not found.
        """
        # VALIDATION LAYER - check inputs before touching database
        if not user_id or not email:
            raise EnrollmentError("user_id and email are required")
        if "@" not in email or not email.strip():
            raise EnrollmentError("invalid email format")
        if not enrollment_key or not enrollment_key.strip():
            raise EnrollmentError("enrollment_key is required")

        # BUSINESS LOGIC LAYER - lookup course
        course = self.db.find_course_by_enrollment_key(enrollment_key)
        if not course:
            raise EnrollmentError(
                f"enrollment key not found: {enrollment_key.strip().upper()}"
            )

        # PERSISTENCE LAYER - create or update enrollment
        self.db.create_or_update_enrollment(
            user_id=user_id,
            email=email,
            course_id=course["course_id"],
            status=config.STATUS_ENROLLED,
        )

        # RETURN SEMANTIC RESULT - fetch and return the record
        record = self.db.find_enrollment_record(user_id, course["course_id"])
        if not record:
            raise EnrollmentError("enrollment failed to persist (unexpected)")
        return record

    def unenroll_student(self, user_id: str, course_id: str) -> bool:
        """
        Soft-unenroll a student by changing their enrollment status.

        This does NOT delete the record, only sets status to 'unenrolled'.

        Args:
            user_id: Student's user ID.
            course_id: Course ID to unenroll from.

        Returns:
            True if unenrollment succeeded.

        Raises:
            EnrollmentError: If inputs invalid or student not found in course.
        """
        if not user_id or not course_id:
            raise EnrollmentError("user_id and course_id are required")

        success = self.db.update_enrollment_status(
            user_id=user_id,
            course_id=course_id,
            new_status=config.STATUS_UNENROLLED,
        )

        if not success:
            raise EnrollmentError(
                f"student {user_id} not enrolled in course {course_id}"
            )
        return True

    def get_student_dashboard(self, user_id: str) -> dict[str, Any]:
        """
        Get dashboard display data for a student (enrolled classes only).

        Business meaning: Show the student their current active enrollments.

        Args:
            user_id: Student's user ID.

        Returns:
            Dict with keys:
                - user_id: The student's ID
                - enrolled_classes: List of enrolled course records
                - enrollment_count: Number of enrolled classes
        """
        enrollments = self.db.find_student_enrollments(
            user_id=user_id, status=config.STATUS_ENROLLED
        )
        return {
            "user_id": user_id,
            "enrolled_classes": enrollments,
            "enrollment_count": len(enrollments),
        }

    def get_student_summary(self, user_id: str) -> dict[str, int]:
        """
        Get summary statistics for a student (count by status).

        Business meaning: Aggregate enrollment records and count by status.
        Includes both enrolled and unenrolled records.

        Args:
            user_id: Student's user ID.

        Returns:
            Dict with keys:
                - total_records: Total enrollment records
                - enrolled: Count of enrolled records
                - unenrolled: Count of unenrolled records
        """
        history = self.db.find_student_enrollment_history(user_id)

        summary = {
            "total_records": len(history),
            config.STATUS_ENROLLED: 0,
            config.STATUS_UNENROLLED: 0,
        }

        for record in history:
            status = record["status"]
            if status in summary:
                summary[status] += 1

        return summary

    def get_available_courses(self) -> list[dict[str, Any]]:
        """
        Get all available courses for enrollment.

        Business meaning: Show students what courses they can enroll in.

        Returns:
            List of course dicts with keys: course_id, course_name, instructor, enrollment_key
        """
        return self.db.find_all_courses()

    def get_enrollment_history(self, user_id: str) -> list[dict[str, Any]]:
        """
        Get complete enrollment history for a student (all statuses).

        Business meaning: Show all courses student has interacted with,
        including unenrolled ones.

        Args:
            user_id: Student's user ID.

        Returns:
            List of enrollment record dicts (joined with course info).
        """
        return self.db.find_student_enrollment_history(user_id)

    def export_dashboard_snapshot(
        self, path: Path = config.SNAPSHOT_PATH
    ) -> None:
        """
        Export database contents to JSON for student inspection.

        Business meaning: Create a snapshot of the seeded database so
        students can inspect how the data is structured.

        Separates concerns:
            1. Fetch all data from database (service layer)
            2. Construct snapshot structure (service layer)
            3. Write JSON to file (I/O)

        Args:
            path: Path to write JSON snapshot. Defaults to config.SNAPSHOT_PATH.
        """
        # Fetch all data (business: "what data should be in snapshot?")
        snapshot_data = {
            "current_student": config.DEFAULT_CURRENT_STUDENT,
            "available_courses": self.db.find_all_courses(),
            "enrollment_records": self.db.find_all_enrollment_records(),
        }

        # Write to file
        json_str = json.dumps(snapshot_data, indent=2)
        path.write_text(json_str, encoding="utf-8")
