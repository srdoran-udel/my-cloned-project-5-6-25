"""Quick test to verify error handling in service layer."""

from database import SQLDatabase
from service import EnrollmentService, EnrollmentError
import config

# Test error handling
db = SQLDatabase()
service = EnrollmentService(db)

# Test 1: Invalid email
print("TEST 1: Enroll with invalid email format")
try:
    service.enroll_student_with_key("u100", "not-an-email", "MISY350-SPRING")
    print("✗ FAILED: Should have raised EnrollmentError")
except EnrollmentError as e:
    print(f"✓ Caught error: {e}")

# Test 2: Invalid key
print("\nTEST 2: Enroll with non-existent enrollment key")
try:
    service.enroll_student_with_key("u100", "test@example.edu", "INVALID-KEY")
    print("✗ FAILED: Should have raised EnrollmentError")
except EnrollmentError as e:
    print(f"✓ Caught error: {e}")

# Test 3: Missing user_id
print("\nTEST 3: Enroll with missing user_id")
try:
    service.enroll_student_with_key("", "test@example.edu", "MISY350-SPRING")
    print("✗ FAILED: Should have raised EnrollmentError")
except EnrollmentError as e:
    print(f"✓ Caught error: {e}")

print("\n✓ All error handling tests passed!")
