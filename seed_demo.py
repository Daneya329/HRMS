"""
Fill the database with realistic demo data (for presentations / screenshots).

    python seed_demo.py

Adds 12 employees, the last 10 days of attendance and some leave requests.
Everything goes through the normal API, so every business rule is respected.
Runs only when there are no employees yet (your own data is never overwritten).
"""
import random
from datetime import date, timedelta

from backend.app import create_app

PEOPLE = [
    ("Ayesha", "Malik", "Female", "Human Resources", "HR Manager", "Full-time", 180000),
    ("Bilal", "Ahmed", "Male", "Engineering", "Senior Software Engineer", "Full-time", 260000),
    ("Sana", "Khan", "Female", "Engineering", "QA Engineer", "Full-time", 140000),
    ("Usman", "Tariq", "Male", "Engineering", "Frontend Developer", "Contract", 160000),
    ("Hira", "Siddiqui", "Female", "Finance", "Accountant", "Full-time", 120000),
    ("Hamza", "Raza", "Male", "Finance", "Finance Intern", "Part-time", 30000),
    ("Mariam", "Javed", "Female", "Sales", "Sales Executive", "Full-time", 95000),
    ("Zain", "Ali", "Male", "Sales", "Sales Lead", "Full-time", 150000),
    ("Fatima", "Noor", "Female", "Marketing", "Content Writer", "Part-time", 45000),
    ("Ahmed", "Hussain", "Male", "Marketing", "Marketing Manager", "Full-time", 200000),
    ("Iqra", "Shah", "Female", "Operations", "Operations Officer", "Full-time", 90000),
    ("Kamran", "Qureshi", "Male", "Operations", "Office Administrator", "Full-time", 70000),
]


def main():
    app = create_app()
    client = app.test_client()
    client.post("/api/login", json={"email": "admin@hrms.local", "password": "Admin@123"})
    if client.get("/api/employees").get_json():
        print("Employees already exist - demo data was NOT added.")
        return
    random.seed(7)
    departments = {d["name"]: d["id"] for d in client.get("/api/departments").get_json()}
    today = date.today()
    ids = []
    for i, (first, last, gender, dept, title, kind, salary) in enumerate(PEOPLE):
        hire = today - timedelta(days=random.randint(60, 2500))
        dob = hire.replace(year=hire.year - random.randint(22, 45), day=min(hire.day, 28))
        response = client.post("/api/employees", json={
            "first_name": first, "last_name": last, "gender": gender, "date_of_birth": dob.isoformat(),
            "email": f"{first}.{last}@company.com".lower(),
            "phone": f"+92 3{random.randint(0, 4)}{i} {1000000 + i * 7919}",
            "cnic": f"{35200 + i}-{1000000 + i * 1234}-{i % 10}", "department_id": departments[dept],
            "designation": title, "hire_date": hire.isoformat(), "employment_type": kind, "salary": salary})
        assert response.status_code == 201, response.get_json()
        ids.append(response.get_json()["id"])

    for back in range(9, -1, -1):
        day = (today - timedelta(days=back)).isoformat()
        for employee_id in ids:
            roll = random.random()
            if roll < 0.08:
                record = {"status": "Absent"}
            elif roll < 0.2:
                record = {"status": "Late", "check_in": f"09:{random.randint(20, 55)}", "check_out": "18:00"}
            elif roll < 0.25:
                record = {"status": "Half Day", "check_in": "09:00", "check_out": "13:00"}
            else:
                record = {"status": "Present", "check_in": f"0{random.randint(8, 8)}:{random.randint(30, 59)}",
                          "check_out": f"17:{random.randint(0, 45):02d}"}
            if back == 0 and random.random() < 0.3:
                continue     # some employees not marked yet today
            response = client.post("/api/attendance", json={"employee_id": employee_id, "date": day, **record})
            assert response.status_code == 201, response.get_json()

    leaves = [(ids[1], "Annual", 7, 11, "Family wedding in Lahore"), (ids[4], "Sick", 2, 3, "Dental surgery"),
              (ids[7], "Casual", 14, 14, "Moving house"), (ids[9], "Annual", 20, 27, "Umrah travel")]
    for employee_id, kind, start, end, reason in leaves:
        response = client.post("/api/leaves", json={
            "employee_id": employee_id, "leave_type": kind, "reason": reason,
            "start_date": (today + timedelta(days=start)).isoformat(),
            "end_date": (today + timedelta(days=end)).isoformat()})
        assert response.status_code == 201, response.get_json()
    first_leave = client.get("/api/leaves").get_json()[-1]
    client.post(f"/api/leaves/{first_leave['id']}/approve", json={})
    print(f"Demo data added: {len(ids)} employees, 10 days of attendance, {len(leaves)} leave requests.")


if __name__ == "__main__":
    main()
