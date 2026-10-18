🎓 College Placement Management System
A full-stack web application developed as a DBMS mini-project to simplify campus placement activities. Students can explore placement drives, check eligibility, apply for jobs, and track application progress. Placement administrators can manage companies and drives, review applications, update selection statuses, and view placement statistics.
<p align="center">
  <strong>Find opportunities. Manage applications. Track placements.</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white" alt="Python 3.10+">
  <img src="https://img.shields.io/badge/Flask-3.0-000000?logo=flask&logoColor=white" alt="Flask 3.0">
  <img src="https://img.shields.io/badge/MySQL-8.0.16%2B-4479A1?logo=mysql&logoColor=white" alt="MySQL 8.0.16+">
  <img src="https://img.shields.io/badge/Bootstrap-5-7952B3?logo=bootstrap&logoColor=white" alt="Bootstrap 5">
</p>

1. Landing page
The home page introduces the portal and provides entry points for students to log in or create an account.
<p align="center"><img src="docs/images/landing-page.png" alt="Placement Portal landing page" width="900"></p>

2. Student dashboard
Students can view their application summary, selection progress, and placement drives for which they may qualify.
<p align="center"><img src="docs/images/student-dashboard.png" alt="Student dashboard with application progress and eligible drives" width="900"></p>

3. Browse placement drives
Students can search available roles, filter eligible opportunities, review packages and eligibility requirements, and apply for drives.
<p align="center"><img src="docs/images/student-drives.png" alt="Student placement drives page" width="900"></p>

4. Administrator dashboard
The dashboard summarizes students, companies, drives, applications, students placed, placement rate, and recent application activity.
<p align="center"><img src="docs/images/admin-dashboard.png" alt="Administrator dashboard with placement statistics" width="900"></p>

5. Application management
Administrators can filter applications, review student and drive details, and update an application's status.
<p align="center"><img src="docs/images/admin-applications.png" alt="Administrator applications management table" width="900"></p>

✨ Features
Student portal
- Student registration, login, and profile management.
- Student profile fields include USN, branch, semester, CGPA, backlogs, graduation year, and skills.
- Browse open placement drives and view eligibility status with reasons.
- Apply to a drive only once; server-side checks prevent duplicate, expired, closed, or ineligible applications.
- Track application progress from Applied to Shortlisted and Selected / Not selected.
- View relevant drives and drives closing soon.
Placement administrator portal
- Add, edit, search, and delete company records.
- Create, edit, and close placement drives.
- Configure minimum CGPA, maximum backlogs, package, application deadline, and required skills.
- Review and filter applications; shortlist, select, or reject applicants.
- View database-backed dashboard statistics.
- Generate placement reports, including eligible students per drive, applications by company, selection percentage, branch statistics, and student placement status.
- Export supported report data as CSV.

🧰 Technology stack
Layer	Technology
Frontend	HTML5, CSS3, JavaScript, Bootstrap 5
Backend	Python, Flask, Flask Blueprints
Database	MySQL 8.0.16+
Database driver	mysql-connector-python
Authentication	Flask sessions and Werkzeug password hashing
Form security	Flask-WTF and CSRF protection
Testing	pytest
Optional deployment	Vercel for the application and a compatible cloud MySQL provider

🏗️ System architecture
The application follows a browser–server–database architecture:
Student / Administrator
          |
          v
    Web Browser
          |
          v
   Flask Application
   ├── Authentication routes
   ├── Student routes
   ├── Administrator routes
   ├── Company and drive routes
   └── Application routes
          |
          v
 Parameterized SQL queries
          |
          v
       MySQL DB
  



