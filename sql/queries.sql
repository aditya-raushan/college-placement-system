USE college_placement_db;

CREATE OR REPLACE VIEW v_application_details AS
SELECT
    a.application_id,
    s.usn,
    u.name AS student_name,
    c.company_name,
    d.drive_id,
    a.applied_at,
    a.status
FROM applications a
JOIN students s ON a.student_id = s.student_id
JOIN users u ON s.user_id = u.user_id
JOIN placement_drives d ON a.drive_id = d.drive_id
JOIN companies c ON d.company_id = c.company_id;

CREATE TABLE IF NOT EXISTS demo_notes (note_id INT PRIMARY KEY AUTO_INCREMENT, note VARCHAR(100) NOT NULL);
ALTER TABLE demo_notes ADD COLUMN created_by VARCHAR(50) NULL;
ALTER TABLE demo_notes MODIFY COLUMN note VARCHAR(200) NOT NULL;
CREATE INDEX idx_demo_created_by ON demo_notes (created_by);
DROP TABLE demo_notes;

INSERT INTO companies (company_name, industry) VALUES ('Demo Corp', 'Testing');
UPDATE companies SET website = 'https://demo.example.com' WHERE company_name = 'Demo Corp';
DELETE FROM companies WHERE company_name = 'Demo Corp';

SELECT s.student_id, s.usn, u.name, u.email, s.branch, s.cgpa, s.backlogs
FROM students s JOIN users u ON u.user_id = s.user_id ORDER BY s.usn;

SELECT * FROM v_application_details ORDER BY applied_at DESC;

SELECT c.company_name, COUNT(a.application_id) AS applications
FROM companies c
LEFT JOIN placement_drives d ON d.company_id = c.company_id
LEFT JOIN applications a ON a.drive_id = d.drive_id
GROUP BY c.company_id, c.company_name ORDER BY applications DESC;

SELECT usn, cgpa FROM students WHERE cgpa > (SELECT AVG(cgpa) FROM students);

SELECT u.name, s.usn, c.company_name, d.job_role, d.package_lpa
FROM applications a
JOIN students s ON s.student_id = a.student_id JOIN users u ON u.user_id = s.user_id
JOIN placement_drives d ON d.drive_id = a.drive_id JOIN companies c ON c.company_id = d.company_id
WHERE a.status = 'selected';

SELECT d.drive_id, c.company_name, d.job_role, COUNT(*) AS selected_students
FROM applications a JOIN placement_drives d ON d.drive_id = a.drive_id
JOIN companies c ON c.company_id = d.company_id
WHERE a.status = 'selected' GROUP BY d.drive_id, c.company_name, d.job_role;

SELECT d.drive_id, d.job_role FROM placement_drives d
WHERE NOT EXISTS (SELECT 1 FROM applications a WHERE a.drive_id = d.drive_id);

CREATE OR REPLACE VIEW v_student_placement_status AS
SELECT
    s.usn,
    u.name,
    s.branch,
    s.cgpa,
    COUNT(a.application_id) AS total_applications
FROM students s
JOIN users u ON u.user_id = s.user_id
LEFT JOIN applications a ON a.student_id = s.student_id
GROUP BY
    s.student_id,
    s.usn,
    u.name,
    s.branch,
    s.cgpa;

SELECT * FROM v_student_placement_status ORDER BY usn;

CREATE OR REPLACE VIEW v_drive_selection_report AS
SELECT
    d.drive_id,
    d.job_role,
    COUNT(a.application_id) AS total_applications,
    SUM(CASE
        WHEN a.status = 'selected' THEN 1
        ELSE 0
    END) AS selected_students,
    ROUND(
        100.0 * SUM(CASE
            WHEN a.status = 'selected' THEN 1
            ELSE 0
        END) / NULLIF(COUNT(a.application_id), 0),
        2
    ) AS selection_percentage
FROM placement_drives d
LEFT JOIN applications a ON a.drive_id = d.drive_id
GROUP BY d.drive_id, d.job_role;

SELECT * FROM v_drive_selection_report ORDER BY selection_percentage DESC;

SELECT branch, COUNT(*) AS students, ROUND(AVG(cgpa),2) AS avg_cgpa, MIN(cgpa) AS min_cgpa, MAX(cgpa) AS max_cgpa
FROM students GROUP BY branch HAVING COUNT(*) >= 2;

SELECT u.name, MAX(d.package_lpa) AS best_package
FROM applications a JOIN students s ON s.student_id = a.student_id JOIN users u ON u.user_id = s.user_id
JOIN placement_drives d ON d.drive_id = a.drive_id
WHERE a.status = 'selected' GROUP BY s.student_id, u.name;

START TRANSACTION;

UPDATE applications
SET status = 'selected'
WHERE application_id = 1;

INSERT INTO selection_results (application_id, result_status)
SELECT application_id, 'selected'
FROM applications
WHERE application_id = 1
ON DUPLICATE KEY UPDATE
    result_status = 'selected';

COMMIT;

SELECT 'users' AS table_name, COUNT(*) AS total FROM users
UNION ALL
SELECT 'students', COUNT(*) FROM students
UNION ALL
SELECT 'companies', COUNT(*) FROM companies
UNION ALL
SELECT 'placement_drives', COUNT(*) FROM placement_drives
UNION ALL
SELECT 'applications', COUNT(*) FROM applications
UNION ALL
SELECT 'selection_results', COUNT(*) FROM selection_results;
USE college_placement_db;

SELECT COUNT(*) FROM users;
SELECT COUNT(*) FROM students;
SELECT COUNT(*) FROM companies;
SELECT COUNT(*) FROM placement_drives;
SELECT COUNT(*) FROM student_skills;
SELECT COUNT(*) FROM drive_skills;
SELECT COUNT(*) FROM applications;
SELECT COUNT(*) FROM selection_results;

SELECT drive_id, job_role, deadline
FROM placement_drives;

SELECT email, role
FROM users;