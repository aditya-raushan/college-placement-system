
USE college_placement_db;

-- WARNING: This resets the demo data in these tables.
SET FOREIGN_KEY_CHECKS = 0;

TRUNCATE TABLE selection_results;
TRUNCATE TABLE applications;
TRUNCATE TABLE drive_skills;
TRUNCATE TABLE student_skills;
TRUNCATE TABLE placement_drives;
TRUNCATE TABLE students;
TRUNCATE TABLE companies;
TRUNCATE TABLE users;

SET FOREIGN_KEY_CHECKS = 1;

-- Temporary non-empty hashes are replaced by seed_db.py
-- with valid Werkzeug password hashes.
INSERT INTO users (name, email, password_hash, role) VALUES
('Aarav Sharma', 'aarav@example.com', 'TEMPORARY_HASH', 'student'),
('Diya Rao', 'diya@example.com', 'TEMPORARY_HASH', 'student'),
('Rohan Kumar', 'rohan@example.com', 'TEMPORARY_HASH', 'student'),
('Ananya Singh', 'ananya@example.com', 'TEMPORARY_HASH', 'student'),
('Ishaan Patel', 'ishaan@example.com', 'TEMPORARY_HASH', 'student'),
('Meera Nair', 'meera@example.com', 'TEMPORARY_HASH', 'student'),
('Kabir Das', 'kabir@example.com', 'TEMPORARY_HASH', 'student'),
('Sana Khan', 'sana@example.com', 'TEMPORARY_HASH', 'student'),
('Arjun Reddy', 'arjun@example.com', 'TEMPORARY_HASH', 'student'),
('Priya Menon', 'priya@example.com', 'TEMPORARY_HASH', 'student'),
('Rahul Verma', 'rahul@example.com', 'TEMPORARY_HASH', 'student'),
('Neha Joshi', 'neha@example.com', 'TEMPORARY_HASH', 'student'),
('Admin User', 'admin@example.com', 'TEMPORARY_HASH', 'admin');

INSERT INTO students
(user_id, usn, branch, semester, cgpa, backlogs, graduation_year)
SELECT user_id, '1NT23AI001', 'AIML', 5, 9.42, 0, 2027 FROM users WHERE email='aarav@example.com'
UNION ALL SELECT user_id, '1NT23AI002', 'AIML', 5, 9.10, 0, 2027 FROM users WHERE email='diya@example.com'
UNION ALL SELECT user_id, '1NT23AI003', 'AIML', 5, 8.85, 0, 2027 FROM users WHERE email='rohan@example.com'
UNION ALL SELECT user_id, '1NT23AI004', 'AIML', 5, 8.70, 0, 2027 FROM users WHERE email='ananya@example.com'
UNION ALL SELECT user_id, '1NT23AI005', 'AIML', 5, 8.50, 0, 2027 FROM users WHERE email='ishaan@example.com'
UNION ALL SELECT user_id, '1NT23AI006', 'CSE', 5, 8.90, 0, 2027 FROM users WHERE email='meera@example.com'
UNION ALL SELECT user_id, '1NT23AI007', 'CSE', 5, 8.20, 1, 2027 FROM users WHERE email='kabir@example.com'
UNION ALL SELECT user_id, '1NT23AI008', 'ISE', 5, 8.60, 0, 2027 FROM users WHERE email='sana@example.com'
UNION ALL SELECT user_id, '1NT23AI009', 'ISE', 5, 7.90, 0, 2027 FROM users WHERE email='arjun@example.com'
UNION ALL SELECT user_id, '1NT23AI010', 'ECE', 5, 8.40, 0, 2027 FROM users WHERE email='priya@example.com'
UNION ALL SELECT user_id, '1NT23AI011', 'ECE', 5, 7.80, 0, 2027 FROM users WHERE email='rahul@example.com'
UNION ALL SELECT user_id, '1NT23AI012', 'AIML', 5, 9.00, 0, 2027 FROM users WHERE email='neha@example.com';

INSERT INTO companies (company_name, industry) VALUES
('Google', 'Technology'),
('Microsoft', 'Technology'),
('Amazon', 'E-commerce'),
('Infosys', 'IT Services'),
('TCS', 'IT Services'),
('Accenture', 'Consulting');

INSERT INTO placement_drives
(company_id, job_role, job_description, minimum_cgpa,
 maximum_backlogs, package_lpa, deadline, status)
VALUES
(1, 'Software Engineer', 'Software development role', 7.00, 0, 24.00, '2026-12-31 23:59:59', 'open'),
(2, 'AI Engineer', 'AI and machine learning role', 7.00, 0, 22.00, '2026-12-31 23:59:59', 'open'),
(3, 'Data Analyst', 'Data analysis role', 6.50, 1, 18.00, '2026-12-31 23:59:59', 'open'),
(4, 'System Engineer', 'IT services role', 6.00, 2, 8.00, '2026-12-31 23:59:59', 'open'),
(5, 'Developer', 'Application development role', 6.00, 1, 7.50, '2026-12-31 23:59:59', 'open'),
(6, 'Data Scientist', 'Data science role', 7.00, 0, 12.00, '2026-12-31 23:59:59', 'open'),
(1, 'ML Engineer', 'Machine learning role', 7.50, 0, 26.00, '2026-12-31 23:59:59', 'open'),
(2, 'Cloud Engineer', 'Cloud infrastructure role', 7.00, 0, 20.00, '2026-12-31 23:59:59', 'open');

INSERT INTO student_skills (student_id, skill_name) VALUES
(1, 'Python'), (1, 'Machine Learning'), (1, 'SQL'),
(2, 'Python'), (2, 'Data Analysis'),
(3, 'C++'), (3, 'Python'),
(4, 'Python'), (4, 'Machine Learning'),
(5, 'Python'), (5, 'SQL'),
(6, 'Data Analysis'), (6, 'SQL'),
(7, 'Java'), (7, 'SQL'),
(8, 'Python'), (8, 'Data Analysis'),
(9, 'Java'), (9, 'Web Development'),
(10, 'Python'), (10, 'SQL'),
(11, 'C++'), (11, 'Java'),
(12, 'Python'), (12, 'Machine Learning');

INSERT INTO drive_skills (drive_id, skill_name) VALUES
(1, 'C++'), (1, 'Data Structures'),
(2, 'Python'), (2, 'Machine Learning'),
(3, 'SQL'), (3, 'Data Analysis'),
(4, 'Java'), (4, 'Problem Solving'),
(5, 'Java'), (5, 'SQL'),
(6, 'Python'), (6, 'Machine Learning'),
(7, 'Python'), (7, 'Machine Learning'),
(8, 'Cloud Computing'), (8, 'Linux');

INSERT INTO applications (student_id, drive_id, applied_at, status) VALUES
(1,1,'2026-01-01 09:00:00','selected'),
(2,1,'2026-01-01 09:30:00','selected'),
(3,1,'2026-01-02 10:00:00','applied'),
(4,1,'2026-01-02 11:00:00','rejected'),
(5,2,'2026-01-03 09:00:00','selected'),
(6,2,'2026-01-03 10:00:00','applied'),
(7,2,'2026-01-04 09:00:00','rejected'),
(8,2,'2026-01-04 11:00:00','applied'),
(9,3,'2026-01-05 09:00:00','selected'),
(10,3,'2026-01-05 10:00:00','applied'),
(11,3,'2026-01-06 09:00:00','rejected'),
(12,3,'2026-01-06 10:00:00','selected'),
(1,4,'2026-01-07 09:00:00','selected'),
(2,4,'2026-01-07 10:00:00','applied'),
(3,4,'2026-01-08 09:00:00','rejected'),
(4,5,'2026-01-08 10:00:00','selected'),
(5,5,'2026-01-09 09:00:00','applied'),
(6,5,'2026-01-09 10:00:00','rejected'),
(7,6,'2026-01-10 09:00:00','selected'),
(8,6,'2026-01-10 10:00:00','applied'),
(9,6,'2026-01-11 09:00:00','rejected'),
(10,7,'2026-01-11 10:00:00','selected'),
(11,7,'2026-01-12 09:00:00','applied'),
(12,7,'2026-01-12 10:00:00','selected'),
(1,8,'2026-01-13 09:00:00','applied'),
(2,8,'2026-01-13 10:00:00','rejected');

INSERT INTO selection_results (application_id, result_status)
SELECT application_id, status
FROM applications
WHERE status IN ('selected', 'rejected');
