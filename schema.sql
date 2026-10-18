-- College Placement Management System
-- Needs MySQL 8.0.16+. WARNING: this file DROPS and recreates all tables.

CREATE DATABASE IF NOT EXISTS college_placement_db
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE college_placement_db;

DROP TABLE IF EXISTS selection_results;
DROP TABLE IF EXISTS applications;
DROP TABLE IF EXISTS drive_skills;
DROP TABLE IF EXISTS student_skills;
DROP TABLE IF EXISTS placement_drives;
DROP TABLE IF EXISTS students;
DROP TABLE IF EXISTS companies;
DROP TABLE IF EXISTS users;

CREATE TABLE users (
    user_id        INT UNSIGNED  NOT NULL AUTO_INCREMENT,
    name           VARCHAR(100)  NOT NULL,
    email          VARCHAR(120)  NOT NULL,
    password_hash  VARCHAR(255)  NOT NULL,
    role           ENUM('admin', 'student', 'company') NOT NULL DEFAULT 'student',
    created_at     TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id),
    CONSTRAINT uq_users_email UNIQUE (email),
    CONSTRAINT chk_users_name  CHECK (CHAR_LENGTH(TRIM(name)) > 0),
    CONSTRAINT chk_users_email CHECK (email LIKE '%_@_%._%'),
    INDEX idx_users_role (role)
) ENGINE=InnoDB;

CREATE TABLE students (
    student_id       INT UNSIGNED      NOT NULL AUTO_INCREMENT,
    user_id          INT UNSIGNED      NOT NULL,
    usn              VARCHAR(20)       NOT NULL,
    branch           VARCHAR(50)       NOT NULL,
    semester         TINYINT UNSIGNED  NOT NULL,
    cgpa             DECIMAL(4,2)      NOT NULL,
    backlogs         TINYINT UNSIGNED  NOT NULL DEFAULT 0,
    graduation_year  SMALLINT UNSIGNED NOT NULL,
    PRIMARY KEY (student_id),
    CONSTRAINT fk_students_user FOREIGN KEY (user_id)
        REFERENCES users (user_id) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT uq_students_user_id UNIQUE (user_id),
    CONSTRAINT uq_students_usn     UNIQUE (usn),
    CONSTRAINT chk_students_usn      CHECK (CHAR_LENGTH(TRIM(usn)) >= 5),
    CONSTRAINT chk_students_semester CHECK (semester BETWEEN 1 AND 8),
    CONSTRAINT chk_students_cgpa     CHECK (cgpa BETWEEN 0 AND 10),
    CONSTRAINT chk_students_backlogs CHECK (backlogs <= 50),
    CONSTRAINT chk_students_gradyear CHECK (graduation_year BETWEEN 2000 AND 2100),
    INDEX idx_students_branch (branch),
    INDEX idx_students_cgpa (cgpa)
) ENGINE=InnoDB;

CREATE TABLE companies (
    company_id    INT UNSIGNED  NOT NULL AUTO_INCREMENT,
    company_name  VARCHAR(120)  NOT NULL,
    industry      VARCHAR(80)   NOT NULL,
    website       VARCHAR(200)  NULL,
    description   TEXT          NULL,
    PRIMARY KEY (company_id),
    CONSTRAINT uq_companies_name UNIQUE (company_name),
    CONSTRAINT chk_companies_name CHECK (CHAR_LENGTH(TRIM(company_name)) > 0)
) ENGINE=InnoDB;

CREATE TABLE placement_drives (
    drive_id          INT UNSIGNED      NOT NULL AUTO_INCREMENT,
    company_id        INT UNSIGNED      NOT NULL,
    job_role          VARCHAR(100)      NOT NULL,
    job_description   TEXT              NULL,
    minimum_cgpa      DECIMAL(4,2)      NOT NULL DEFAULT 0.00,
    maximum_backlogs  TINYINT UNSIGNED  NOT NULL DEFAULT 0,
    package_lpa       DECIMAL(6,2)      NOT NULL,
    deadline          DATETIME          NOT NULL,
    status            ENUM('open', 'closed') NOT NULL DEFAULT 'open',
    created_at        TIMESTAMP         NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (drive_id),
    CONSTRAINT fk_drives_company FOREIGN KEY (company_id)
        REFERENCES companies (company_id) ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT chk_drives_role     CHECK (CHAR_LENGTH(TRIM(job_role)) > 0),
    CONSTRAINT chk_drives_mincgpa  CHECK (minimum_cgpa BETWEEN 0 AND 10),
    CONSTRAINT chk_drives_backlogs CHECK (maximum_backlogs <= 50),
    CONSTRAINT chk_drives_package  CHECK (package_lpa >= 0),
    INDEX idx_drives_status_deadline (status, deadline)
) ENGINE=InnoDB;

CREATE TABLE student_skills (
    student_id  INT UNSIGNED  NOT NULL,
    skill_name  VARCHAR(50)   NOT NULL,
    PRIMARY KEY (student_id, skill_name),
    CONSTRAINT fk_sskills_student FOREIGN KEY (student_id)
        REFERENCES students (student_id) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT chk_sskills_name CHECK (CHAR_LENGTH(TRIM(skill_name)) > 0),
    INDEX idx_sskills_skill (skill_name)
) ENGINE=InnoDB;

CREATE TABLE drive_skills (
    drive_id    INT UNSIGNED  NOT NULL,
    skill_name  VARCHAR(50)   NOT NULL,
    PRIMARY KEY (drive_id, skill_name),
    CONSTRAINT fk_dskills_drive FOREIGN KEY (drive_id)
        REFERENCES placement_drives (drive_id) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT chk_dskills_name CHECK (CHAR_LENGTH(TRIM(skill_name)) > 0),
    INDEX idx_dskills_skill (skill_name)
) ENGINE=InnoDB;

CREATE TABLE applications (
    application_id  INT UNSIGNED  NOT NULL AUTO_INCREMENT,
    student_id      INT UNSIGNED  NOT NULL,
    drive_id        INT UNSIGNED  NOT NULL,
    applied_at      TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status          ENUM('applied', 'shortlisted', 'selected', 'rejected')
                    NOT NULL DEFAULT 'applied',
    PRIMARY KEY (application_id),
    CONSTRAINT uq_application_student_drive UNIQUE (student_id, drive_id),
    CONSTRAINT fk_app_student FOREIGN KEY (student_id)
        REFERENCES students (student_id) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_app_drive FOREIGN KEY (drive_id)
        REFERENCES placement_drives (drive_id) ON DELETE RESTRICT ON UPDATE CASCADE,
    INDEX idx_app_drive_status (drive_id, status),
    INDEX idx_app_status (status)
) ENGINE=InnoDB;

CREATE TABLE selection_results (
    result_id       INT UNSIGNED  NOT NULL AUTO_INCREMENT,
    application_id  INT UNSIGNED  NOT NULL,
    result_status   ENUM('selected', 'rejected') NOT NULL,
    updated_at      TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP
                    ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (result_id),
    CONSTRAINT uq_result_application UNIQUE (application_id),
    CONSTRAINT fk_result_application FOREIGN KEY (application_id)
        REFERENCES applications (application_id) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB;