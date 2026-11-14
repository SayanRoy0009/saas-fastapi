import os
import random
from datetime import datetime, timedelta
from faker import Faker
import mysql.connector
from dotenv import load_dotenv

load_dotenv()

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_USER = os.getenv("DB_USER", "root")
DB_PASS = os.getenv("DB_PASS", "")
DB_NAME = os.getenv("DB_NAME", "saas_fastapi")

fake = Faker()

def seed(num_users=50):
    print(f"Connecting to database '{DB_NAME}' as '{DB_USER}'...")
    db = mysql.connector.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASS,
        database=DB_NAME
    )
    cursor = db.cursor()

    # Get plan IDs
    cursor.execute("SELECT id, name FROM plans")
    plan_rows = cursor.fetchall()
    if not plan_rows:
        print("No plans found in database! Please run init_db.py first.")
        return

    plan_map = {name: pid for pid, name in plan_rows}

    print(f"Generating {num_users} mock customers and subscriptions...")
    for _ in range(num_users):
        username = fake.user_name()
        email = fake.email()
        password = "dummy_hashed_password"
        created_at = fake.date_time_between(start_date="-6M", end_date="now")

        cursor.execute(
            "INSERT INTO users (username, email, password, created_at, role) VALUES (%s, %s, %s, %s, %s)",
            (username, email, password, created_at, "customer")
        )
        user_id = cursor.lastrowid

        # Randomly assign plan
        plan_name = random.choice(["Free", "Basic", "Pro", "Premium"])
        plan_id = None if plan_name == "Free" else plan_map.get(plan_name)
        start_date = created_at + timedelta(days=random.randint(1, 10))

        cursor.execute(
            "INSERT INTO subscriptions (user_id, plan_id, start_date) VALUES (%s, %s, %s)",
            (user_id, plan_id, start_date)
        )

    db.commit()
    cursor.close()
    db.close()
    print(f"Successfully added {num_users} mock customers and subscriptions into '{DB_NAME}'!")

if __name__ == "__main__":
    seed(50)
