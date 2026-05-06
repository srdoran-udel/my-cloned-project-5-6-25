"""
Module 8 Student Enrollment backend starter.

This file demonstrates the refactored layered architecture with:
    - config.py: Constants, paths, static configuration
    - database.py: SQLDatabase class for low-level SQLite operations
    - service.py: EnrollmentService class for business logic and validation
    - This file: Entry point and test runner

App idea:
    - a student opens a dashboard
    - the dashboard shows enrolled classes
    - the student enters an enrollment key to join another class
    - the database stores courses and enrollment records
    - a JSON snapshot is exported so students can inspect the seeded data

Focus:
    - student enrollment behavior
    - local SQLite database
    - enrollment keys
    - soft unenroll using status = "unenrolled"
    - clean separation of concerns (config, database, service)

Out of scope:
    - Streamlit UI
    - authentication/session state
    - caching
    - export formatting
    - production health checks

Run with:
    python enrollment_starter.py
"""

from __future__ import annotations

import config
from database import SQLDatabase
from service import EnrollmentService, EnrollmentError


def main() -> None:
    """
    Setup demo: initialize database, seed data, run test flow.

    This demonstrates the layered architecture:
        1. Database layer: Create tables, seed data
        2. Service layer: Business operations with validation
        3. CLI: Present results
    """
    # Initialize database layer
    db = SQLDatabase(db_path=config.DB_PATH)
    db.create_tables()
    db.seed_courses(config.AVAILABLE_COURSE_KEYS)
    db.seed_enrollments(config.SAMPLE_ENROLLMENTS)

    # Initialize service layer
    current_user = config.DEFAULT_CURRENT_STUDENT
    service = EnrollmentService(
        database=db,
        current_user_id=current_user["user_id"],
    )

    # Run test flow
    user_id = current_user["user_id"]
    email = current_user["email"]

    print("Current student:")
    print(current_user)

    print("\nAvailable courses:")
    print(service.get_available_courses())

    print("\nInitial enrolled classes:")
    dashboard = service.get_student_dashboard(user_id)
    print(f"Dashboard: {dashboard}")

    print("\nStudent enters key DATA210-SPRING:")
    try:
        result = service.enroll_student_with_key(
            user_id=user_id,
            email=email,
            enrollment_key="DATA210-SPRING",
        )
        print(f"Enrollment result: {result}")
    except EnrollmentError as e:
        print(f"Enrollment failed: {e}")

    print("\nUpdated enrolled classes:")
    dashboard = service.get_student_dashboard(user_id)
    print(f"Dashboard: {dashboard}")

    print("\nStudent summary:")
    print(service.get_student_summary(user_id))

    print("\nExporting snapshot...")
    service.export_dashboard_snapshot()
    print(f"Snapshot written to: {config.SNAPSHOT_PATH}")


if __name__ == "__main__":
    main()
