"""TEMPORARY: adds one company and 4 sample drives so you can test Phase 4.
Run once:  python dev_sample_drives.py   (safe to run again, it skips if present)
"""
import mysql.connector

from config import Config

conn = mysql.connector.connect(**Config.DB_CONFIG)
cur = conn.cursor()

cur.execute("SELECT company_id FROM companies WHERE company_name = %s", ("Demo Tech Pvt Ltd",))
row = cur.fetchone()
if row:
    print("Demo data already present. Nothing to do.")
else:
    cur.execute("INSERT INTO companies (company_name, industry) VALUES (%s, %s)",
                ("Demo Tech Pvt Ltd", "IT Services"))
    company_id = cur.lastrowid
    drives = [
        # role, min_cgpa, max_backlogs, package, days_until_deadline
        ("Easy Role", 6.0, 2, 4.0, 10),
        ("Mid Role", 7.5, 0, 6.5, 10),
        ("High CGPA Role", 9.0, 0, 12.0, 10),
        ("Expired Role", 6.0, 2, 5.0, -3),
    ]
    for role, min_cgpa, max_backlogs, package, days in drives:
        cur.execute(
            "INSERT INTO placement_drives (company_id, job_role, job_description, "
            "minimum_cgpa, maximum_backlogs, package_lpa, deadline, status) "
            "VALUES (%s, %s, %s, %s, %s, %s, DATE_ADD(NOW(), INTERVAL %s DAY), 'open')",
            (company_id, role, f"Sample description for {role}.", min_cgpa,
             max_backlogs, package, days),
        )
        if role == "Easy Role":
            cur.executemany("INSERT INTO drive_skills (drive_id, skill_name) VALUES (%s, %s)",
                            [(cur.lastrowid, "Python"), (cur.lastrowid, "SQL")])
    conn.commit()
    print("Added Demo Tech Pvt Ltd with 4 sample drives.")

cur.close()
conn.close()