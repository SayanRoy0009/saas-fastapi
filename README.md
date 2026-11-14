# SaaS Admin Portal 
---

## 🚀 Features
- **FastAPI Backend**: High-performance asynchronous REST and HTML routes.
- **Session Authentication**: Role-based access control with secure cookie sessions.
- **Admin Dashboard**: Live metrics for customers, subscriptions, and plans with Chart.js visualizations.
- **Plan Management**: Create, edit, and delete subscription tiers with custom quotas.
- **Customer Directory**: Search, filter by plan, date-range filters, and pagination.
- **Subscription Analytics**: Filterable subscription listings and 12-month visual growth trend charts.
- **100% Password Hash Compatible**: Uses `werkzeug.security` so existing passwords from your Flask database work immediately.

---

## 🛠️ Prerequisites & Setup

### 1. Open the project in VS Code
Open VS Code and choose **File > Open Folder...** and select:
```
Project\saas-fastapi
```

### 2. Set Up a Virtual Environment (Recommended)
Open a terminal in VS Code (`Ctrl + ~`) and run:
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

*(If script execution is disabled on your system, run `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process` first)*

### 3. Install Dependencies
Install all required packages from `requirements.txt`:
```powershell
pip install -r requirements.txt
```

### 4. Database Setup (MySQL)
Ensure your MySQL server is running.
If you already set up the `saas_project` database for the Flask project, you can use it directly!

If setting up fresh, run the commands in `sql.txt`:
```sql
CREATE DATABASE saas_project;
USE saas_project;
CREATE USER 'flaskuser'@'localhost' IDENTIFIED BY 'flaskpass';
GRANT ALL PRIVILEGES ON saas_project.* TO 'flaskuser'@'localhost';
```
Execute the table creation queries in `sql.txt`.

*(Optional)* To populate mock data for charts and customers:
```powershell
python seed_data.py
```

---

## ▶️ How to Run

### Method 1: Python Runner
```powershell
python run.py
```

### Method 2: Uvicorn Directly
```powershell
uvicorn main:app --reload
```

### Method 3: VS Code Run & Debug
1. Press `Ctrl + Shift + D` (or click the Run & Debug icon on the sidebar).
2. Select **"FastAPI: Run SaaS Project"**.
3. Press `F5` to start debugging.

---

## 🌐 Accessing the Application
Once running, open your browser:
- Application URL: **http://127.0.0.1:8000**
- Interactive Swagger API Docs: **http://127.0.0.1:8000/docs**
- ReDoc Docs: **http://127.0.0.1:8000/redoc**

Login with your admin account (`username: admin`) to access the dashboard at `/dashboard`.
