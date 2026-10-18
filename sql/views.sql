
-- Report views for College Placement Management System

USE college_placement_db;

-- 1. Application details report
CREATE OR REPLACE VIEW v_application_details AS
SELECT
    a.application_id,
    a.status,
    a.applied_at,
    s.student_id,
    s.usn,
    u.name AS student_name,
    s.branch,
    s.cgpa,
    d.drive_id,
    d.job_role,
    d.package_lpa,
    c.company_id,
    c.company_name
FROM applications AS a
JOIN students AS s
    ON s.student_id = a.student_id
JOIN users AS u
    ON u.user_id = s.user_id
JOIN placement_drives AS d
    ON d.drive_id = a.drive_id
JOIN companies AS c
    ON c.company_id = d.company_id;

-- 2. Student placement status report
CREATE OR REPLACE VIEW v_student_placement_status AS
SELECT
    s.student_id,
    s.usn,
    u.name,
    s.branch,
    s.cgpa,
    s.backlogs,
    COUNT(a.application_id) AS total_applications,
    COUNT(
        CASE WHEN a.status = 'selected' THEN 1 END
    ) AS selected_count,
    CASE
        WHEN COUNT(
            CASE WHEN a.status = 'selected' THEN 1 END
        ) > 0 THEN 'Placed'
        WHEN COUNT(a.application_id) > 0 THEN 'In process'
        ELSE 'Not applied'
    END AS placement_status
FROM students AS s
JOIN users AS u
    ON u.user_id = s.user_id
LEFT JOIN applications AS a
    ON a.student_id = s.student_id
GROUP BY
    s.student_id,
    s.usn,
    u.name,
    s.branch,
    s.cgpa,
    s.backlogs;

-- 3. Drive selection report
CREATE OR REPLACE VIEW v_drive_selection_report AS
SELECT
    d.drive_id,
    c.company_name,
    d.job_role,
    COUNT(a.application_id) AS applicants,
    COUNT(
        CASE WHEN a.status = 'selected' THEN 1 END
    ) AS selected,
    COALESCE(
        ROUND(
            100.0 * COUNT(
                CASE WHEN a.status = 'selected' THEN 1 END
            ) / NULLIF(COUNT(a.application_id), 0),
            2
        ),
        0
    ) AS selection_percentage
FROM placement_drives AS d
JOIN companies AS c
    ON c.company_id = d.company_id
LEFT JOIN applications AS a
    ON a.drive_id = d.drive_id
GROUP BY
    d.drive_id,
    c.company_name,
    d.job_role;
