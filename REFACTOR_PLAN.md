# Backend Refactor Plan: From Procedural to Layered OO Design

**Goal:** Separate database operations, business logic, and configuration into clean, testable layers.

**Current State:** 390-line monolithic procedural file with mixed concerns.

**Target State:** 4 focused modules with single responsibilities.

---

## 1. New Architecture

### Layer Structure

```
enrollment_starter.py (Entry Point)
├── config.py              Database constants, status enums, static config
├── database.py            SQLDatabase class with row-level operations
├── service.py             EnrollmentService class with business logic
└── models.py (optional)   Type definitions, return objects
```

### Dependency Flow

```
┌──────────────────────────────────────────────────┐
│ enrollment_starter.py (CLI / main runner)        │
└──────────────┬───────────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────────┐
│ service.py (EnrollmentService)                   │
│  - Business logic & validation                   │
│  - Coordinates database calls                    │
│  - Returns semantic results                      │
└──────────────┬───────────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────────┐
│ database.py (SQLDatabase class)                  │
│  - Pure row queries: SELECT, INSERT, UPDATE      │
│  - Connection management                         │
│  - No business logic                             │
└──────────────┬───────────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────────┐
│ config.py (Constants & Configuration)            │
│  - DB_PATH, SNAPSHOT_PATH                        │
│  - Status constants, default values              │
└──────────────────────────────────────────────────┘
```

---

## 2. File-by-File Breakdown

### **config.py** – Configuration & Constants

**Responsibility:** Single source of truth for paths, statuses, and static configuration.

**Contents:**

```python
# Paths
DB_PATH = Path(__file__).with_name("student_enrollment_practice.db")
SNAPSHOT_PATH = Path(__file__).with_name("student_enrollment_snapshot.json")

# Status enum-like constants
STATUS_ENROLLED = "enrolled"
STATUS_UNENROLLED = "unenrolled"

# Schema defaults
DEFAULT_STATUS = STATUS_ENROLLED

# Seeding data (move from starter.py)
AVAILABLE_COURSE_KEYS = [...]  # 3 courses
SAMPLE_ENROLLMENTS = [...]      # 4 sample records

# Session/Default user (will be overridden in UI)
DEFAULT_CURRENT_STUDENT = {
    "user_id": "u100",
    "name": "Maya Patel",
    "email": "maya.patel@example.edu",
}
```

**Risk Mitigations:**
- ✓ Centralized configuration → easy to swap for tests or production
- ✓ Constants don't "leak" into multiple files
- ✓ Clear distinction between static data and session state

**Migration:**
- Move lines 36-89 from `enrollment_starter.py` to `config.py`

---

### **database.py** – SQLDatabase Class (Database Layer)

**Responsibility:** Pure SQLite operations. No business logic. No validation beyond parameterized queries.

**Design Pattern:** Dependency injection of DB path.

**Class:** `SQLDatabase`

```python
class SQLDatabase:
    def __init__(self, db_path: Path = config.DB_PATH):
        self.db_path = db_path
    
    # Connection management
    def _connect(self) -> sqlite3.Connection:
        """Internal: open and return a connection."""
    
    # DDL (Schema)
    def create_tables(self) -> None:
        """Create courses and enrollments tables if not exist."""
    
    # Seeding
    def seed_courses(self, courses: list[dict]) -> None:
        """Insert course records."""
    
    def seed_enrollments(self, enrollments: list[tuple]) -> None:
        """Insert enrollment records."""
    
    # Read operations (single responsibility each)
    def find_course_by_enrollment_key(self, key: str) -> Optional[dict]:
        """SELECT * FROM courses WHERE enrollment_key = ?"""
    
    def find_enrollment_record(self, user_id: str, course_id: str) -> Optional[dict]:
        """SELECT * FROM enrollments WHERE user_id=? AND course_id=?"""
    
    def find_student_enrollments(self, user_id: str, status: str) -> list[dict]:
        """SELECT * FROM enrollments JOIN courses WHERE user_id=? AND status=?"""
    
    def find_student_enrollment_history(self, user_id: str) -> list[dict]:
        """SELECT * FROM enrollments JOIN courses WHERE user_id=? (all statuses)"""
    
    def find_all_courses(self) -> list[dict]:
        """SELECT * FROM courses ORDER BY course_id"""
    
    def find_all_enrollment_records(self) -> list[dict]:
        """SELECT * FROM enrollments JOIN courses"""
    
    # Write operations
    def create_or_update_enrollment(
        self,
        user_id: str,
        email: str,
        course_id: str,
        status: str,
    ) -> None:
        """INSERT OR REPLACE enrollment record."""
    
    def update_enrollment_status(
        self,
        user_id: str,
        course_id: str,
        new_status: str,
    ) -> bool:
        """UPDATE enrollments SET status WHERE user_id=? AND course_id=?"""
        # Returns True if row affected, False if no row found
```

**Key Principles:**
- ✓ Each method does ONE operation
- ✓ All methods are parameterized (no SQL injection)
- ✓ Returns simple dicts/lists (row data), not objects
- ✓ No business logic (no "user_id validation", no "is-this-a-valid-email")
- ✓ Testable with mock data or in-memory SQLite

**Migration:**
- Move lines 51-56 (`connect()`) → becomes `_connect()` private method
- Move lines 59-89 (`create_tables()`) → becomes `create_tables()` method
- Move lines 92-97 (`seed_sample_data()`) → split into `seed_courses()` and `seed_enrollments()`
- Move lines 100-102 (`rows_to_dicts()`) → becomes private utility
- Move lines 105-150 (all query functions) → become methods with clear names

---

### **service.py** – EnrollmentService Class (Business Logic Layer)

**Responsibility:** Business rules, validation, coordination, semantic meaning.

**Class:** `EnrollmentService`

```python
class EnrollmentService:
    def __init__(self, database: SQLDatabase, current_user_id: str):
        self.db = database
        self.current_user_id = current_user_id
    
    # Business operations with semantic meaning
    
    def enroll_student_with_key(
        self,
        user_id: str,
        email: str,
        enrollment_key: str,
    ) -> dict[str, Any]:
        """
        Enroll a student using an enrollment key.
        
        Validates:
            - user_id is not empty
            - email is valid format
            - enrollment_key is not empty
            - enrollment_key exists in courses table
        
        Returns enrollment record or raises EnrollmentError.
        """
        # VALIDATION LAYER
        if not user_id or not email:
            raise EnrollmentError("user_id and email required")
        if "@" not in email:
            raise EnrollmentError("invalid email format")
        if not enrollment_key:
            raise EnrollmentError("enrollment_key required")
        
        # BUSINESS LOGIC LAYER
        course = self.db.find_course_by_enrollment_key(
            enrollment_key.strip().upper()
        )
        if not course:
            raise EnrollmentError(f"enrollment key not found: {enrollment_key}")
        
        # PERSISTENCE LAYER
        self.db.create_or_update_enrollment(
            user_id=user_id,
            email=email,
            course_id=course["course_id"],
            status=config.STATUS_ENROLLED,
        )
        
        # RETURN SEMANTIC RESULT
        record = self.db.find_enrollment_record(user_id, course["course_id"])
        if not record:
            raise EnrollmentError("enrollment failed to persist")
        return record
    
    def unenroll_student(
        self,
        user_id: str,
        course_id: str,
    ) -> bool:
        """Soft-unenroll by setting status to unenrolled."""
        if not user_id or not course_id:
            raise EnrollmentError("user_id and course_id required")
        
        success = self.db.update_enrollment_status(
            user_id=user_id,
            course_id=course_id,
            new_status=config.STATUS_UNENROLLED,
        )
        if not success:
            raise EnrollmentError(f"Student not enrolled in {course_id}")
        return True
    
    def get_student_dashboard(self, user_id: str) -> dict[str, Any]:
        """
        Get all enrolled courses for dashboard display.
        
        Returns:
            {
                "user_id": "u100",
                "enrolled_classes": [...],
                "enrollment_count": 3,
            }
        """
        enrollments = self.db.find_student_enrollments(
            user_id=user_id,
            status=config.STATUS_ENROLLED,
        )
        return {
            "user_id": user_id,
            "enrolled_classes": enrollments,
            "enrollment_count": len(enrollments),
        }
    
    def get_student_summary(self, user_id: str) -> dict[str, int]:
        """
        Count enrollments by status for a student.
        
        Returns:
            {
                "total_records": 5,
                "enrolled": 3,
                "unenrolled": 2,
            }
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
    
    def export_dashboard_snapshot(self, path: Path = config.SNAPSHOT_PATH) -> None:
        """
        Export database state to JSON for inspection.
        
        Separate concerns:
            1. Fetch all data (this layer)
            2. Format JSON (formatting layer)
            3. Write file (I/O layer)
        """
        snapshot_data = {
            "current_student": config.DEFAULT_CURRENT_STUDENT,
            "available_courses": self.db.find_all_courses(),
            "enrollment_records": self.db.find_all_enrollment_records(),
        }
        
        # Write to file
        json_str = json.dumps(snapshot_data, indent=2)
        path.write_text(json_str, encoding="utf-8")
    
    def get_available_courses(self) -> list[dict[str, Any]]:
        """Return all available courses."""
        return self.db.find_all_courses()
    
    def get_enrollment_history(self, user_id: str) -> list[dict[str, Any]]:
        """Return all enrollments (enrolled + unenrolled) for user."""
        return self.db.find_student_enrollment_history(user_id)
```

**Error Handling:**

```python
class EnrollmentError(Exception):
    """Base exception for enrollment business logic errors."""
    pass
```

**Key Principles:**
- ✓ All validation happens here (not in database layer)
- ✓ Calls database with validated inputs
- ✓ Returns semantic results (structured dicts with meaning)
- ✓ Raises specific exceptions for business errors
- ✓ Testable: can inject mock SQLDatabase

**Migration:**
- `enroll_with_key()` → `enroll_student_with_key()` (refactored)
- `soft_unenroll_student()` → `unenroll_student()` (refactored)
- `get_student_summary()` → same logic, cleaner
- `get_student_enrollments()` → `get_student_dashboard()` (semantic name)
- `export_database_snapshot()` → `export_dashboard_snapshot()` (refactored)
- NEW: `get_available_courses()`, `get_enrollment_history()` (service wrappers)

---

### **enrollment_starter.py** (Refactored Entry Point)

**Responsibility:** CLI/testing runner. Orchestrates setup. Minimal logic.

**Structure:**

```python
from pathlib import Path
from config import (
    DB_PATH, SNAPSHOT_PATH, STATUS_ENROLLED, 
    AVAILABLE_COURSE_KEYS, SAMPLE_ENROLLMENTS, 
    DEFAULT_CURRENT_STUDENT
)
from database import SQLDatabase
from service import EnrollmentService, EnrollmentError


def main() -> None:
    """Setup demo: create tables, seed data, run test flow."""
    
    # 1. Initialize database layer
    db = SQLDatabase(db_path=DB_PATH)
    db.create_tables()
    db.seed_courses(AVAILABLE_COURSE_KEYS)
    db.seed_enrollments(SAMPLE_ENROLLMENTS)
    
    # 2. Initialize service layer
    current_user = DEFAULT_CURRENT_STUDENT
    service = EnrollmentService(
        database=db,
        current_user_id=current_user["user_id"]
    )
    
    # 3. Run test flow
    user_id = current_user["user_id"]
    email = current_user["email"]
    
    print("Current student:", current_user)
    
    print("\nAvailable courses:")
    print(service.get_available_courses())
    
    print("\nInitial dashboard:")
    print(service.get_student_dashboard(user_id))
    
    print("\nEnrolling in DATA210-SPRING...")
    try:
        result = service.enroll_student_with_key(
            user_id=user_id,
            email=email,
            enrollment_key="DATA210-SPRING",
        )
        print("Enrollment result:", result)
    except EnrollmentError as e:
        print(f"Enrollment failed: {e}")
    
    print("\nUpdated dashboard:")
    print(service.get_student_dashboard(user_id))
    
    print("\nStudent summary:")
    print(service.get_student_summary(user_id))
    
    print("\nExporting snapshot...")
    service.export_dashboard_snapshot()
    print(f"Snapshot written to: {SNAPSHOT_PATH}")


if __name__ == "__main__":
    main()
```

**Migration:**
- Delete all functions from current file—move to appropriate layers
- Keep only `main()` entry point
- Import and use service/database classes

---

## 3. Function Migration Matrix

| Current Function | New Location | New Name | Changes |
|---|---|---|---|
| `connect()` | `database.py` | `SQLDatabase._connect()` | Private method |
| `create_tables()` | `database.py` | `SQLDatabase.create_tables()` | Method, unchanged logic |
| `seed_sample_data()` | `database.py` | `SQLDatabase.seed_courses()` + `.seed_enrollments()` | Split into two methods |
| `rows_to_dicts()` | `database.py` | `SQLDatabase._rows_to_dicts()` | Private utility |
| `get_available_course_keys()` | `database.py` | `SQLDatabase.find_all_courses()` | Clearer name |
| `get_course_by_key()` | `database.py` | `SQLDatabase.find_course_by_enrollment_key()` | Clearer name |
| `get_student_enrollments()` | `database.py` | `SQLDatabase.find_student_enrollments()` | Base query |
| `get_student_enrollment_history()` | `database.py` | `SQLDatabase.find_student_enrollment_history()` | Clearer name |
| `get_student_course_record()` | `database.py` | `SQLDatabase.find_enrollment_record()` | Clearer name |
| `enroll_with_key()` | `service.py` | `EnrollmentService.enroll_student_with_key()` | Add validation, error handling |
| `soft_unenroll_student()` | `service.py` | `EnrollmentService.unenroll_student()` | Add error handling |
| `get_student_summary()` | `service.py` | `EnrollmentService.get_student_summary()` | Same logic |
| `export_database_snapshot()` | `service.py` | `EnrollmentService.export_dashboard_snapshot()` | Same logic, clearer naming |
| Module constants | `config.py` | Same names | No change |
| `main()` | `enrollment_starter.py` | `main()` | Refactored to use classes |

---

## 4. Benefits of This Refactor

### **Testability**

```python
# Before: Can't test enroll_with_key without real database
def test_enroll_with_key():
    enroll_with_key("u100", "test@example.edu", "MISY350-SPRING")  # ← Uses real DB!

# After: Mock the database layer
def test_enroll_with_key():
    mock_db = MockSQLDatabase()
    service = EnrollmentService(db=mock_db, current_user_id="u100")
    result = service.enroll_student_with_key(...)  # ← Uses mock!
```

### **Maintainability**

```
Before:  Change to enrollment validation? Grep 5+ functions, understand flow.
After:   Change to enrollment validation? Edit EnrollmentService.enroll_student_with_key().
```

### **Reusability**

```python
# Before: Can't use just the "lookup course" logic without database connection
# After: Yes you can!
db = SQLDatabase()
course = db.find_course_by_enrollment_key("MISY350-SPRING")
```

### **Extensibility**

```python
# Before: Adding audit logging means modifying enroll_with_key + SQL + export
# After: Add to service or create an AuditService that wraps calls
class AuditedEnrollmentService(EnrollmentService):
    def enroll_student_with_key(self, ...):
        result = super().enroll_student_with_key(...)
        self.audit.log(f"User {user_id} enrolled in {course_id}")
        return result
```

### **Configuration**

```python
# Before: To use different DB, modify code
DB_PATH = Path(__file__).with_name("test.db")  # Hardcoded

# After: Pass at runtime
db = SQLDatabase(db_path=Path("./test.db"))
```

---

## 5. Migration Strategy (No Breaking Changes)

### **Phase 1: Create new modules (parallel)**
- Write `config.py` alongside existing code
- Write `database.py` alongside existing code
- Write `service.py` alongside existing code
- All new code works independently

### **Phase 2: Test new structure**
- Run `main()` with new classes to verify behavior matches old code
- Current `enrollment_starter.py` still works

### **Phase 3: Cutover**
- Update `enrollment_starter.py` to use new classes
- Delete old functions (keep `main()` entry point)
- Keep `student_enrollment_snapshot.json` unchanged

### **Phase 4: Extend**
- Add tests for each layer independently
- Layer-by-layer validation and error handling

---

## 6. Implementation Checklist

- [ ] Create `config.py` with constants
- [ ] Create `database.py` with `SQLDatabase` class
  - [ ] Connection management
  - [ ] Schema creation
  - [ ] Seeding methods
  - [ ] Read methods (find_*)
  - [ ] Write methods (create/update/delete)
- [ ] Create `service.py` with `EnrollmentService` class
  - [ ] Business validation
  - [ ] Enrollment orchestration
  - [ ] Error handling (EnrollmentError)
  - [ ] Dashboard/summary logic
  - [ ] Export logic
- [ ] Refactor `enrollment_starter.py`
  - [ ] Delete old functions
  - [ ] Import new classes
  - [ ] Rewrite `main()` to use classes
- [ ] **Manual test:** Run new code, verify output matches old code
- [ ] **Commit:** `git commit -m "refactor: move to layered OO architecture"`

---

## 7. Post-Refactor Enhancements (Optional)

These become much easier with clean layers:

```python
# 1. Add logging to database layer
class SQLDatabase:
    def find_course_by_enrollment_key(self, key: str):
        logger.debug(f"Looking up course with key: {key}")
        ...

# 2. Add metrics/monitoring to service
class EnrollmentService:
    def enroll_student_with_key(self, ...):
        with metrics.timer("enroll_duration"):
            ...

# 3. Add caching to database (without breaking service)
class CachedSQLDatabase(SQLDatabase):
    def find_course_by_enrollment_key(self, key: str):
        if key in self._cache:
            return self._cache[key]
        result = super().find_course_by_enrollment_key(key)
        self._cache[key] = result
        return result

# 4. Add soft-delete or audit history
class SQLDatabase:
    def find_student_enrollment_history(self, user_id: str, include_deleted=False):
        where_clause = "WHERE user_id = ?" if include_deleted else "WHERE user_id = ? AND deleted_at IS NULL"
        ...
```

---

## Summary

| Aspect | Before | After |
|--------|--------|-------|
| **Structure** | 1 flat file | 4 focused modules |
| **Layers** | Mixed | Separated (config, DB, service) |
| **Testing** | Requires real DB | Can mock each layer |
| **Error Handling** | Generic `None` | Specific exceptions |
| **Extensibility** | Hard (modify existing functions) | Easy (inherit/compose) |
| **Maintainability** | High coupling | Low coupling |
| **Configuration** | Hardcoded | Dependency injection |
| **Line Count** | 390 | ~350 (more readable) |

---

## Implementation Prompt (Use After Approval)

```
I APPROVE THE REFACTOR PLAN. Implement as follows:

1. Create config.py with all constants moved from enrollment_starter.py
2. Create database.py with SQLDatabase class:
   - Private _connect() method
   - create_tables() method implementing existing schema
   - seed_courses(courses) and seed_enrollments(enrollments) methods
   - find_* methods for all SELECT queries (clear names)
   - create_or_update_enrollment() and update_enrollment_status() for writes
   - Private _rows_to_dicts() utility
   
3. Create service.py with EnrollmentService class:
   - EnrollmentError exception
   - __init__(database, current_user_id)
   - enroll_student_with_key() with validation and error handling
   - unenroll_student() with validation and error handling
   - get_student_dashboard() returning enrolled classes + count
   - get_student_summary() aggregating by status
   - export_dashboard_snapshot() writing JSON
   - get_available_courses() and get_enrollment_history() helper methods
   
4. Refactor enrollment_starter.py:
   - Delete all old functions
   - Import classes and config
   - Rewrite main() to instantiate SQLDatabase and EnrollmentService
   - Keep same test flow (init → courses → enroll → summary → export)
   
5. Verify:
   - Code runs without errors
   - Output matches original (courses, enrollments, summaries)
   - student_enrollment_snapshot.json created correctly
   
6. Test:
   - Run twice to verify idempotency (seed uses INSERT OR IGNORE)
   - Check that re-enrolling a unenrolled student works
   - Check that enrolling in non-existent key raises EnrollmentError
   
Prioritize clarity over brevity. Add docstrings. Use type hints. Follow existing code style.
```
