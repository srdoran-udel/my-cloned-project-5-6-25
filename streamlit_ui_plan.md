# Streamlit UI Plan

## 1. App Goal and User Assumptions

- The app assumes the student is already logged in.
- The simulated/current student for this Streamlit UI is:
  - **Name:** Maya Patel
  - **User ID:** u100
  - **Email:** maya.patel@example.edu
- The UI should behave as if the student is already authenticated and ready to use the dashboard.

## 2. Assumptions: Do

- Use the existing seeded or simulated student from the backend config.
- Verify the student role in session state before rendering pages.
- Store the following values in `st.session_state`:
  - `st.session_state["role"]` – student role, such as `"student"`
  - `st.session_state["page"]` – current page, such as `"dashboard"` or `"class"`
  - `st.session_state["selected_class_id"]` – selected course ID for the class page
  - `st.session_state["message"]` – feedback message text
  - `st.session_state["message_type"]` – feedback type: `success`, `warning`, `error`
- Keep the UI focused on the existing seeded student and seeded data.

## 3. Assumptions: Do Not

- Do not build login screens.
- Do not add registration or account creation flows.
- Do not implement password handling or authentication services.
- Do not create a new auth system in this session.

## 4. Existing Backend Structure to Follow

The UI plan must follow the Session 1 multi-layer design and call the service layer. The UI should use these files and classes:

- `config.py`
  - `DEFAULT_CURRENT_STUDENT`
  - `AVAILABLE_COURSE_KEYS`
  - `SAMPLE_ENROLLMENTS`
  - `DB_PATH`, `SNAPSHOT_PATH`
- `database.py`
  - `SQLDatabase` class
- `service.py`
  - `EnrollmentService` class
  - `EnrollmentError` exception
  - Methods to call from UI:
    - `EnrollmentService.enroll_student_with_key(user_id, email, enrollment_key)`
    - `EnrollmentService.unenroll_student(user_id, course_id)`
    - `EnrollmentService.get_student_dashboard(user_id)`
    - `EnrollmentService.get_student_summary(user_id)`
    - `EnrollmentService.get_available_courses()`
    - `EnrollmentService.get_enrollment_history(user_id)`
    - `EnrollmentService.export_dashboard_snapshot(path)`
- `enrollment_starter.py`
  - Example entry point and demo flow

### Design Rule

- The UI should call the service layer directly.
- It should make minimal changes to other layers.
- The database layer remains focused on SQLite queries and rows.
- Business meaning remains in the service layer.

## 5. Routing and Session State

### Page Navigation

- Use `st.session_state["page"]` to control the current page.
- Possible values:
  - `"dashboard"` – student dashboard page
  - `"class"` – selected class detail page

### Navigation Controls

- A "Dashboard" button returns to the dashboard page.
- A "Go to Class" button sets `st.session_state["selected_class_id"]` and changes `st.session_state["page"] = "class"`.
- The class page should have a "Back to Dashboard" button.
- When `st.session_state["page"]` changes, clear `st.session_state["message"]` and `st.session_state["message_type"]` so feedback is not stale.

### Session State Fields

- `st.session_state["role"]` should be set to `"student"`.
- `st.session_state["page"]` should default to `"dashboard"`.
- `st.session_state["selected_class_id"]` should default to `None`.
- `st.session_state["message"]` should hold the latest feedback text.
- `st.session_state["message_type"]` should hold one of `success`, `warning`, or `error`.

## 6. Page 1: Student Dashboard

### Layout

- Page title: **Student Dashboard**
- Subtitle: current student name and email.
- Summary panel with counts:
  - enrolled classes count
  - total records count
  - unenrolled count
- Enrollment key entry area:
  - `st.text_input("Enter enrollment key")`
  - `st.button("Enroll")`
- Render the course list using individual rows or containers, not a static dataframe.
- For each enrolled course row/container:
  - Course ID
  - Course name
  - Instructor
  - `Go to Class` button
  - `Unenroll` button
- A feedback area for success/warning/error messages.

### Streamlit Elements

- `st.title("Student Dashboard")`
- `st.subheader(...)`
- `st.info(...)` or `st.metric(...)` for totals
- `st.text_input(...)` for enrollment key entry
- `st.button("Enroll")` to submit key
- Individual row containers for enrolled classes to support actionable buttons
- `st.button("Go to Class")` and `st.button("Unenroll")` per-course
- `st.empty()` placeholder to display messages

## 7. Page 2: Selected Class Page

### Layout

- Page title: **Class Details** or course name.
- Display basic class info:
  - Course ID
  - Course name
  - Instructor
  - Enrollment key (optional or hidden if sensitive)
  - Enrollment status
  - Enrollment date
- Action buttons:
  - `Back to Dashboard`
  - `Unenroll` if the student is currently enrolled
- Optionally show a course description placeholder if helpful.

### Streamlit Elements

- `st.title(...)` or `st.header(...)`
- `st.write(...)` for course details
- `st.button("Back to Dashboard")`
- `st.button("Unenroll")` if appropriate
- `st.info(...)` for current enrollment status
- `st.warning(...)` if the class is not currently enrolled

## 8. Actions and Feedback

### Enrollment Behavior

- When the student enters a key and taps Enroll:
  - UI calls `service.enroll_student_with_key(...)`
  - On success, set `st.session_state["message"]` to a success message and message type to `success`
  - Refresh dashboard data by rereading `service.get_student_dashboard(user_id)` and `service.get_student_summary(user_id)`
  - If the class is already enrolled, the service should behave as a reactivation or update and UI should show a success refresh.

### Unenroll Behavior

- When the student clicks Unenroll:
  - UI calls `service.unenroll_student(user_id, course_id)`
  - On success, set `st.session_state["message_type"] = "success"` and a message like "Unenrolled successfully."
  - Refresh the dashboard list and counts.
  - This should perform a soft unenroll by updating status only.

### Messages

- Use message area or `st.alert` equivalent in Streamlit:
  - `st.success(...)` for success
  - `st.warning(...)` for warnings
  - `st.error(...)` for errors
- Examples:
  - Success: "Enrollment successful."
  - Warning: "Course is already enrolled." or "This student cannot enroll in that key."
  - Error: "Invalid enrollment key." or "Error saving enrollment."
- Store text and type in session state so page refreshes preserve the message until cleared.

### Refresh Behavior

- After any action, reload relevant data from the service layer:
  - `service.get_student_dashboard(user_id)`
  - `service.get_student_summary(user_id)`
  - `service.get_enrollment_history(user_id)` if needed
- Optionally use `st.experimental_rerun()` after state updates or simply rerender with updated state.

## 9. Plan Output

This should be delivered as a clear Markdown implementation plan before any code changes.

The plan should include:
- A page layout description for Dashboard and Selected Class
- `st.session_state` variables and routing behavior
- The exact service methods to call
- How to keep the UI minimal and layered
- A statement that no authentication/login flow will be added

## 10. Prompt for AI

Use this prompt for the next step:

```
Draft a Streamlit UI implementation plan for a student enrollment app.
The app should assume the student is already logged in as Maya Patel (user_id u100).
Do not add login, registration, password handling, or authentication.
Follow the existing backend layer design from Session 1:
- config.py
- database.py with SQLDatabase
- service.py with EnrollmentService and EnrollmentError
- enrollment_starter.py as the entry point

Keep enrollment-key logic in the service layer.
Keep summary/counting logic in the service layer.
Keep the database focused on SQLite queries and returning rows.
Keep soft unenroll as a status update, not a deletion.
Keep the JSON snapshot export in the backend and do not change it.

Explain how Streamlit pages are handled using `st.session_state`.
Use keys: `page`, `role`, `selected_class_id`, `message`, and `message_type`.
Describe two pages:
- Student Dashboard
- Selected Class Page

Include:
- layout and Streamlit elements for each page
- navigation and session state flow
- actions and feedback for enroll and unenroll
- service methods the UI should call
- a plan output section so the response is a reviewable Markdown plan

Do not write any Streamlit code in this prompt.
```
