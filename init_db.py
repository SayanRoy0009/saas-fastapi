import os
import getpass
import mysql.connector
from werkzeug.security import generate_password_hash
from dotenv import load_dotenv

# Load .env file if present
load_dotenv()

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_USER = os.getenv("DB_USER", "root")
DB_PASS = os.getenv("DB_PASS", "")
DB_NAME = os.getenv("DB_NAME", "saas_fastapi")


def run_init():
    global DB_HOST, DB_USER, DB_PASS, DB_NAME
    print("=" * 60)
    print(f"  FastAPI SaaS Database Setup: [{DB_NAME}]")
    print("=" * 60)

    # Allow interactive confirmation or credential override if needed
    print(f"Connecting with current settings:")
    print(f"  Host: {DB_HOST}")
    print(f"  User: {DB_USER}")
    print(f"  Database to create: {DB_NAME}")
    
    conn = None
    try:
        # Try connecting with initial credentials
        conn = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASS
        )
    except mysql.connector.Error as err:
        print(f"\n[!] Connection failed with user '{DB_USER}' (Error: {err.msg})")
        print("Please enter your MySQL credentials to initialize the database:")
        DB_HOST = input("MySQL Host [localhost]: ").strip() or "localhost"
        DB_USER = input("MySQL User [root]: ").strip() or "root"
        DB_PASS = getpass.getpass(f"MySQL Password for '{DB_USER}': ")
        try:
            conn = mysql.connector.connect(
                host=DB_HOST,
                user=DB_USER,
                password=DB_PASS
            )
        except mysql.connector.Error as err2:
            print(f"\n[ERROR] Unable to connect to MySQL: {err2}")
            return False

    cursor = conn.cursor()
    print(f"\n[*] Creating database '{DB_NAME}' if not exists...")
    cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{DB_NAME}` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
    cursor.execute(f"USE `{DB_NAME}`")

    print("[*] Creating table 'users'...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(50) NOT NULL UNIQUE,
            email VARCHAR(100) NOT NULL UNIQUE,
            password VARCHAR(500) NOT NULL,
            role ENUM('admin', 'customer') DEFAULT 'customer',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    print("[*] Creating table 'plans'...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS plans (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            price DECIMAL(10,2) NOT NULL,
            description TEXT,
            max_projects INT DEFAULT 10,
            max_team_size INT DEFAULT 5,
            target_user VARCHAR(50) DEFAULT 'personal',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    print("[*] Creating table 'subscriptions'...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS subscriptions (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            plan_id INT NULL,
            start_date DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (plan_id) REFERENCES plans(id) ON DELETE SET NULL
        )
    """)

    # Seed default plans if empty
    cursor.execute("SELECT COUNT(*) FROM plans")
    if cursor.fetchone()[0] == 0:
        print("[*] Inserting default subscription tiers...")
        plans = [
            ("Free", 0.00, "For personal use or evaluation", 10, 5, "personal"),
            ("Basic", 14.99, "Ideal for small businesses", 50, 25, "small"),
            ("Pro", 24.99, "Best for growing teams", 100, 50, "mid"),
            ("Premium", 49.99, "For large organizations", 250, 100, "large"),
        ]
        cursor.executemany("""
            INSERT INTO plans (name, price, description, max_projects, max_team_size, target_user)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, plans)

    # Seed default admin user if not exists
    cursor.execute("SELECT COUNT(*) FROM users WHERE username = 'admin'")
    if cursor.fetchone()[0] == 0:
        print("[*] Creating default admin account (username: admin, password: admin123)...")
        hashed_admin_pass = generate_password_hash("admin123")
        cursor.execute("""
            INSERT INTO users (username, email, password, role)
            VALUES ('admin', 'admin@example.com', %s, 'admin')
        """, (hashed_admin_pass,))

    conn.commit()

    # Save credentials into .env file for the FastAPI app
    env_content = f"""# SaaS FastAPI Database Configuration
DB_HOST={DB_HOST}
DB_USER={DB_USER}
DB_PASS={DB_PASS}
DB_NAME={DB_NAME}
SECRET_KEY=fastapi-saas-super-secret-key-12345
"""
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    with open(env_path, "w", encoding="utf-8") as f:
        f.write(env_content)

    cursor.close()
    conn.close()

    print("\n" + "=" * 60)
    print("  [SUCCESS] Database 'saas_fastapi' initialized successfully!")
    print(f"  Configuration saved to: {env_path}")
    print("  Default Admin Login:")
    print("    Username: admin")
    print("    Password: admin123")
    print("=" * 60)
    print("\nNext step: Run 'python run.py' to launch your FastAPI app.")
    return True


if __name__ == "__main__":
    run_init()
