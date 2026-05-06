"""Database layer for student enrollment system.

This module contains the SQLDatabase class which handles all
low-level SQLite operations. It is purely data-focused with no business logic.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Optional

import config


class SQLDatabase:
    """SQLite database connection and operations for enrollment system."""

    def __init__(self, db_path: Path = config.DB_PATH) -> None:
        """
        Initialize database with a path.

        Args:
            db_path: Path to SQLite database file. Defaults to config.DB_PATH.
        """
        self.db_path = db_path

    def _connect(self) -> sqlite3.Connection:
        """
        Open and return a database connection.

        Returns:
            sqlite3.Connection with row_factory set to sqlite3.Row.
        """
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _rows_to_dicts(self, rows: list[sqlite3.Row]) -> list[dict[str, Any]]:
        """
        Convert SQLite rows into dictionaries.

        Args:
            rows: List of sqlite3.Row objects.

        Returns:
            List of dictionaries with same data.
        """
        return [dict(row) for row in rows]

    def create_tables(self) -> None:
        """
        Create the courses and enrollments tables if they don't exist.

        Creates two tables:
            - courses: course_id, course_name, instructor, enrollment_key
            - enrollments: enrollment_id, user_id, email, course_id, status, enrolled_at
        """
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS courses (
                    course_id TEXT PRIMARY KEY,
                    course_name TEXT NOT NULL,
                    instructor TEXT NOT NULL,
                    enrollment_key TEXT NOT NULL UNIQUE
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS enrollments (
                    enrollment_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    email TEXT NOT NULL,
                    course_id TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'enrolled',
                    enrolled_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, course_id),
                    FOREIGN KEY(course_id) REFERENCES courses(course_id)
                )
                """
            )

    def seed_courses(self, courses: list[dict[str, str]]) -> None:
        """
        Insert course records into courses table.

        Uses INSERT OR IGNORE to allow idempotent calls.

        Args:
            courses: List of dicts with keys: course_id, course_name, instructor, enrollment_key
        """
        with self._connect() as connection:
            connection.executemany(
                """
                INSERT OR IGNORE INTO courses (
                    course_id, course_name, instructor, enrollment_key
                )
                VALUES (?, ?, ?, ?)
                """,
                [
                    (
                        course["course_id"],
                        course["course_name"],
                        course["instructor"],
                        course["enrollment_key"],
                    )
                    for course in courses
                ],
            )

    def seed_enrollments(
        self, enrollments: list[tuple[str, str, str, str]]
    ) -> None:
        """
        Insert enrollment records into enrollments table.

        Uses INSERT OR IGNORE to allow idempotent calls.

        Args:
            enrollments: List of tuples (user_id, email, course_id, status)
        """
        with self._connect() as connection:
            connection.executemany(
                """
                INSERT OR IGNORE INTO enrollments (user_id, email, course_id, status)
                VALUES (?, ?, ?, ?)
                """,
                enrollments,
            )

    # READ operations: Single responsibility per method

    def find_all_courses(self) -> list[dict[str, Any]]:
        """
        Get all courses ordered by course_id.

        Returns:
            List of course dicts with keys: course_id, course_name, instructor, enrollment_key
        """
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT course_id, course_name, instructor, enrollment_key
                FROM courses
                ORDER BY course_id
                """
            ).fetchall()

        return self._rows_to_dicts(rows)

    def find_course_by_enrollment_key(self, enrollment_key: str) -> Optional[dict[str, Any]]:
        """
        Find a course by its enrollment key.

        Args:
            enrollment_key: The enrollment key to search for.

        Returns:
            Course dict if found, None otherwise.
        """
        if not enrollment_key:
            return None

        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT course_id, course_name, instructor, enrollment_key
                FROM courses
                WHERE enrollment_key = ?
                """,
                (enrollment_key.strip().upper(),),
            ).fetchone()

        return dict(row) if row else None

    def find_enrollment_record(
        self, user_id: str, course_id: str
    ) -> Optional[dict[str, Any]]:
        """
        Get one student's enrollment record for one course.

        Args:
            user_id: Student user ID.
            course_id: Course ID.

        Returns:
            Enrollment dict if found, None otherwise.
        """
        if not user_id or not course_id:
            return None

        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT enrollment_id, user_id, email, course_id, status, enrolled_at
                FROM enrollments
                WHERE user_id = ? AND course_id = ?
                """,
                (user_id, course_id),
            ).fetchone()

        return dict(row) if row else None

    def find_student_enrollments(
        self, user_id: str, status: str
    ) -> list[dict[str, Any]]:
        """
        Get all enrollment records for a student with a specific status.

        Args:
            user_id: Student user ID.
            status: Status to filter by (e.g., 'enrolled', 'unenrolled').

        Returns:
            List of enrollment dicts joined with course info.
        """
        if not user_id:
            return []

        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    e.enrollment_id,
                    e.user_id,
                    e.email,
                    e.course_id,
                    c.course_name,
                    c.instructor,
                    e.status,
                    e.enrolled_at
                FROM enrollments e
                JOIN courses c ON c.course_id = e.course_id
                WHERE e.user_id = ? AND e.status = ?
                ORDER BY c.course_id
                """,
                (user_id, status),
            ).fetchall()

        return self._rows_to_dicts(rows)

    def find_student_enrollment_history(self, user_id: str) -> list[dict[str, Any]]:
        """
        Get all enrollment records for a student (all statuses).

        Args:
            user_id: Student user ID.

        Returns:
            List of all enrollment dicts for this student.
        """
        if not user_id:
            return []

        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    e.enrollment_id,
                    e.user_id,
                    e.email,
                    e.course_id,
                    c.course_name,
                    c.instructor,
                    e.status,
                    e.enrolled_at
                FROM enrollments e
                JOIN courses c ON c.course_id = e.course_id
                WHERE e.user_id = ?
                ORDER BY c.course_id
                """,
                (user_id,),
            ).fetchall()

        return self._rows_to_dicts(rows)

    def find_all_enrollment_records(self) -> list[dict[str, Any]]:
        """
        Get all enrollment records in the entire database.

        Used for database snapshots and exports.

        Returns:
            List of all enrollment dicts joined with course info.
        """
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    e.enrollment_id,
                    e.user_id,
                    e.email,
                    e.course_id,
                    c.course_name,
                    c.instructor,
                    e.status,
                    e.enrolled_at
                FROM enrollments e
                JOIN courses c ON c.course_id = e.course_id
                ORDER BY e.user_id, e.course_id
                """
            ).fetchall()

        return self._rows_to_dicts(rows)

    # WRITE operations: Single responsibility per method

    def create_or_update_enrollment(
        self, user_id: str, email: str, course_id: str, status: str
    ) -> None:
        """
        Insert or update an enrollment record.

        Uses INSERT OR REPLACE to handle both new enrollments and reactivations.

        Args:
            user_id: Student user ID.
            email: Student email.
            course_id: Course to enroll in.
            status: Enrollment status (usually 'enrolled').
        """
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO enrollments (user_id, email, course_id, status)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(user_id, course_id)
                DO UPDATE SET
                    email = excluded.email,
                    status = excluded.status,
                    enrolled_at = CURRENT_TIMESTAMP
                """,
                (user_id, email, course_id, status),
            )

    def update_enrollment_status(
        self, user_id: str, course_id: str, new_status: str
    ) -> bool:
        """
        Update the status of an enrollment record (e.g., soft unenroll).

        Args:
            user_id: Student user ID.
            course_id: Course ID.
            new_status: New status to set.

        Returns:
            True if a row was updated, False if no row matched.
        """
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE enrollments
                SET status = ?
                WHERE user_id = ? AND course_id = ?
                """,
                (new_status, user_id, course_id),
            )

        return cursor.rowcount > 0
